import asyncio, csv, os, subprocess, psutil, json, redis, logging, itertools, numpy, struct
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from redis import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address

from .default import (
  ENVIRONMENT,
  DEFAULT_REDIS_URI,
  ROOT,
  FRAMEWORK_FOLDER,
  TEMP_FOLDER,
  BUNDLE_FOLDER,
  RATE_LIMIT,
  RATE_LIMIT_LOCAL,
  REDIS_EXPIRATION,
  REDIS_HOST,
  REDIS_PORT,
  DATA_SIZE_LOWERBOUND,
  DATA_SIZE_UPPERBOUND,
  RESOURCE_SAFETY_MARGIN,
  MODEL_THRESHOLD_FRACTION,
  MODEL_ROOT,
  OUTPUT_CONSISTENCY,
  EOS_TMP_TASKS,
  generic_example_input_file,
  generic_example_output_file,
  cprint,
)


CHUNK_MULTIPLIER = 4


def resolve_dtype(dtype):
  if dtype.lower() == "integer":
    return numpy.int32
  if dtype.lower() == "float":
    return numpy.float32
  return str


def write_smiles_bin(chunk, out_file):
  smiles_list = list(chunk)
  meta = {
    "columns": ["input"],
    "count": len(smiles_list),
  }
  meta_bytes = (json.dumps(meta) + "\n").encode("utf-8")

  with open(out_file, "wb") as f:
    f.write(meta_bytes)
    for s in smiles_list:
      b = s.encode("utf-8")
      f.write(struct.pack(">I", len(b)))
      f.write(b)


def read_bin(path):
  if not os.path.exists(path):
    raise FileNotFoundError(f"{path!r} not found")

  with open(path, "rb") as f:
    header_line = f.readline()
    if not header_line:
      raise ValueError(f"{path!r} is empty or missing header")
    try:
      meta = json.loads(header_line.decode("utf-8").rstrip("\n"))
    except json.JSONDecodeError as e:
      raise ValueError(f"Invalid JSON header in {path!r}: {header_line!r}") from e

    rows, cols = meta["shape"]
    dtype = numpy.dtype(meta.get("dtype"))
    columns = meta["columns"]
    offset = f.tell()

  arr = numpy.memmap(
    path,
    mode="r",
    dtype=dtype,
    offset=offset,
    shape=(rows, cols),
  )
  return arr.tolist(), columns


def compute_memory_usage() -> float:
  process = psutil.Process(os.getpid())
  mem_bytes = process.memory_info().rss
  return mem_bytes / (1024 * 1024)


def compute_max_model_size_threshold():
  return MODEL_THRESHOLD_FRACTION * available_mem_total()


def get_model_dir_size(path):
  total_size = 0
  try:
    with os.scandir(path) as entries:
      for entry in entries:
        try:
          if entry.is_file(follow_symlinks=False):
            total_size += entry.stat(follow_symlinks=False).st_size
          elif entry.is_dir(follow_symlinks=False):
            total_size += get_model_dir_size(entry.path)
        except Exception:
          continue
  except Exception:
    return 0
  return int(total_size)


model_size_byte = get_model_dir_size(MODEL_ROOT)


def make_hashable(obj):
  if isinstance(obj, list):
    return tuple(make_hashable(x) for x in obj)
  elif isinstance(obj, dict):
    return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
  return obj


def orient_to_json(values, columns, index, orient, output_type):
  if len(output_type) > 1:
    output_type = "string"
  else:
    output_type = output_type[0].lower()

  def convert_value(x):
    if x is None or x == "":
      return None
    if isinstance(x, numpy.generic):
      x = x.item()
    if output_type == "string":
      return str(x)
    if output_type == "float":
      if isinstance(x, (list, numpy.ndarray)) and len(x) > 0:
        x = x[0]
      try:
        return float(x)
      except (ValueError, TypeError):
        return None
    if output_type == "integer":
      if isinstance(x, (list, numpy.ndarray)) and len(x) > 0:
        x = x[0]
      try:
        return int(x)
      except (ValueError, TypeError):
        try:
          f = float(x)
        except (ValueError, TypeError):
          return None
        return int(f) if f.is_integer() else int(f)
    return x

  try:
    n = len(values)
  except TypeError:
    n = values.size if isinstance(values, numpy.ndarray) else 0

  if n > 0 and isinstance(values[0], (list, numpy.ndarray)):
    serialized = [[convert_value(cell) for cell in row] for row in values]
  else:
    serialized = [convert_value(cell) for cell in values]

  if orient == "split":
    return {"columns": columns, "index": index, "data": serialized}
  elif orient == "records":
    return [dict(zip(columns, row)) for row in serialized]
  elif orient == "index":
    return {idx: dict(zip(columns, row)) for idx, row in zip(index, serialized)}
  elif orient == "columns":
    data = {}
    for col_idx, col in enumerate(columns):
      col_data = {}
      for row_idx, idx_val in enumerate(index):
        col_data[make_hashable(idx_val)] = serialized[row_idx][col_idx]
      data[col] = col_data
    return data
  elif orient == "values":
    return serialized

  return None


def conn_redis():
  redis_client = Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
  redis_client.ping()
  return redis_client


def init_redis():
  global redis_client
  try:
    redis_client = conn_redis()
    cprint("Redis connected", fg="green", bold=True)
    return True
  except redis.ConnectionError:
    redis_client = None
    cprint("Redis not connected", fg="yellow", bold=True)
    return False


def get_api_names_from_sh(framework_dir):
  if not os.path.exists(framework_dir):
    return

  api_names = []
  for l in os.listdir(framework_dir):
    if l.endswith(".sh"):
      api_names += [l.split(".sh")[0]]
  if len(api_names) == 0:
    raise Exception("No API names found. An API should be a .sh file")
  return api_names


def get_example_path(example_file):
  example_path = os.path.join(FRAMEWORK_FOLDER, "examples", example_file)
  api_name = get_api_names_from_sh(FRAMEWORK_FOLDER)
  if api_name:
    api_name = api_name[0]
    if not os.path.exists(example_path):
      example_path = os.path.join(
        FRAMEWORK_FOLDER, "examples", f"{api_name}_{example_file}"
      )
      return example_path
  return example_path


try:
  to_thread = asyncio.to_thread
except AttributeError:

  async def to_thread(func, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, func, *args, **kwargs)


async def load_card_metadata(bundle_folder: str):
  file_path = os.path.join(bundle_folder, "information.json")
  contents = await to_thread(_read_file, file_path)
  return json.loads(contents)


def _read_file(file_path: str) -> str:
  with open(file_path, "r") as f:
    return f.read()


async def get_metadata():
  data = await load_card_metadata(BUNDLE_FOLDER)
  return data["card"]


def get_sync_metadata():
  file_path = os.path.join(BUNDLE_FOLDER, "information.json")
  if os.path.exists(file_path):
    contents = _read_file(file_path)
    return json.loads(contents)


def read_example():
  example_input_path = get_example_path(generic_example_input_file)
  if not os.path.exists(example_input_path):
    return []

  with open(example_input_path, "r") as f:
    reader = csv.reader(f)
    next(reader)
    data = [x[0] for x in reader]
  return data


def load_csv_data(file_path: str):
  example_input_path = get_example_path(file_path)
  with open(example_input_path, "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)
  return header, rows


def rate_limit():
  if ENVIRONMENT == "prod":
    return RATE_LIMIT
  else:
    return RATE_LIMIT_LOCAL


def create_limiter():
  if ENVIRONMENT != "prod":
    return Limiter(
      key_func=get_remote_address,
    )
  try:
    conn_redis()
  except redis.ConnectionError:
    if ENVIRONMENT == "prod":
      raise redis.ConnectionError("Redis is not initialized!")

  return Limiter(
    key_func=get_remote_address,
    storage_uri=DEFAULT_REDIS_URI,
  )


def extract_input(data):
  if data and isinstance(data[0], dict) and "input" in data[0]:
    return [d["input"] for d in data]
  return data


def input_has_key(data):
  if data and isinstance(data[0], dict) and "key" in data[0]:
    return True
  return False


def split_data(data, num_chunks):
  if num_chunks <= 0:
    return [data]
  chunk_size = len(data) // num_chunks
  remainder = len(data) % num_chunks
  chunks, start = [], 0
  for i in range(num_chunks):
    end = start + chunk_size + (1 if i < remainder else 0)
    chunks.append(data[start:end])
    start = end
  return chunks


def available_mem():
  return psutil.virtual_memory().available


def available_mem_total():
  return psutil.virtual_memory().total


def get_cpu_count(logical):
  return psutil.cpu_count(logical=logical)


def generate_resp_body(results, output_type, header):
  dtype = resolve_dtype(output_type)
  n_rows = len(results)
  n_cols = len(results[0]) if n_rows else 0
  flat_iter = itertools.chain.from_iterable(results)
  arr = numpy.fromiter(flat_iter, dtype=dtype, count=n_rows * n_cols)
  arr = arr.reshape((n_rows, n_cols))
  del results
  info = {"dims": header, "shape": [n_rows, n_cols], "dtype": arr.dtype.str}
  header_line = (json.dumps(info) + "\n").encode("utf-8")
  body = arr.tobytes()
  return header_line + body


def resource_planner(data, max_workers):
  total_mem = available_mem()
  model_mem = model_size_byte or 1
  safety_mem = int(total_mem * RESOURCE_SAFETY_MARGIN)
  max_workers_by_mem = max(1, safety_mem // model_mem)
  phys_cores = get_cpu_count(logical=False) or get_cpu_count(logical=True) or 1
  max_workers_by_cpu = max(1, phys_cores - 1)
  data_workers = len(data) if data else 1
  num_workers = min(max_workers, max_workers_by_mem, max_workers_by_cpu, data_workers)
  cprint(
    f"Resource planner - mem_limit: {max_workers_by_mem}, cpu_limit: {max_workers_by_cpu}, data_limit: {data_workers}, selected: {num_workers}",
    fg="blue",
  )
  return num_workers


def compute_num_workers(data, max_workers, min_workers):
  workers = resource_planner(data, max_workers)
  workers = max(workers, min_workers)
  if data and workers > len(data):
    workers = len(data)
  cprint(f"Using {workers} workers (min: {min_workers}, max: {max_workers})", fg="blue")
  return workers


def run_in_parallel(num_workers, tag, chunks, model_id, task_type, timeout=None):
  cprint(f"ProcessPool tasks: {len(chunks)} | workers: {num_workers}", fg="blue")
  results = []
  headers = []
  with ProcessPoolExecutor(max_workers=num_workers) as executor:
    for chunk_result, header in executor.map(
      process_chunk,
      chunks,
      range(len(chunks)),
      itertools.repeat(tag),
      itertools.repeat(model_id),
      itertools.repeat(task_type),
      timeout=timeout,
    ):
      results.extend(chunk_result)
      headers.append(header)
  return results, (headers[0] if headers else None)


def run_in_threads(num_workers, tag, chunks, model_id, task_type, timeout=None):
  cprint(f"ThreadPool tasks: {len(chunks)} | workers: {num_workers}", fg="blue")
  results = []
  headers = []
  with ThreadPoolExecutor(max_workers=num_workers) as executor:
    for chunk_result, header in executor.map(
      process_chunk,
      chunks,
      range(len(chunks)),
      itertools.repeat(tag),
      itertools.repeat(model_id),
      itertools.repeat(task_type),
      timeout=timeout,
    ):
      results.extend(chunk_result)
      headers.append(header)
  return results, (headers[0] if headers else None)


def compute_parallel(data, tag, max_workers, min_workers, metadata, task_type):
  num_workers = compute_num_workers(data, max_workers, min_workers)
  os.environ["MAX_WORKERS"] = str(num_workers)
  max_chunks = num_workers * CHUNK_MULTIPLIER
  chunk_count = min(len(data), max_chunks) if data else 1
  chunks = split_data(data, chunk_count)
  cprint(f"Scheduling {len(chunks)} chunks across {num_workers} workers", fg="blue")

  if not is_model_variable(metadata) and len(data) < (num_workers * 10):
    return run_in_threads(num_workers, tag, chunks, metadata["Identifier"], task_type)
  else:
    return run_in_parallel(num_workers, tag, chunks, metadata["Identifier"], task_type)


def run_sequential_data(tag, data, model_id, task_type):
  return process_chunk(data, 0, tag, model_id, task_type)


def is_model_variable(metadata):
  if OUTPUT_CONSISTENCY in metadata:
    if metadata[OUTPUT_CONSISTENCY] == "Variable":
      return True
  if "Generative" in metadata["Task"]:
    return True
  return False


def is_parallel_amenable(data, metadata):
  model_size_thres = compute_max_model_size_threshold()
  if model_size_byte > model_size_thres and len(data) >= int(DATA_SIZE_LOWERBOUND):
    return True
  elif model_size_byte < model_size_thres and len(data) >= int(DATA_SIZE_UPPERBOUND):
    return True
  return False


def compute_results(data, tag, max_workers, min_workers, metadata, task_type):
  parallel_amenable = is_parallel_amenable(data, metadata)
  cprint(f"Amenable for multiprocessing: {parallel_amenable}", fg="blue")
  if parallel_amenable:
    return compute_parallel(data, tag, max_workers, min_workers, metadata, task_type)
  else:
    return run_sequential_data(tag, data, metadata["Identifier"], task_type)


def _process_chunk_simple(chunk, chunk_idx, base_tag, model_id):
  tag = f"{base_tag}_{chunk_idx}"
  input_f = os.path.join(TEMP_FOLDER, f"input-{tag}.csv")
  output_f = os.path.join(TEMP_FOLDER, f"output-{tag}.csv")
  try:
    with open(input_f, "w", newline="") as csvfile:
      writer = csv.writer(csvfile)
      writer.writerow(["input"])
      for item in chunk:
        writer.writerow([item])

    cmd = f"conda run -n test bash {FRAMEWORK_FOLDER}/run.sh {FRAMEWORK_FOLDER} {input_f} {output_f} {ROOT}"
    subprocess.run(cmd, shell=True, check=True)
    with open(output_f, "r", newline="") as csvfile:
      reader = csv.reader(csvfile)
      rows = list(reader)
    header = rows[0] if rows else []
    results = rows[1:] if len(rows) > 1 else []
  finally:
    for fpath in [input_f, output_f]:
      if os.path.exists(fpath):
        os.remove(fpath)
  return results, header


def _process_chunk_heavy(chunk, chunk_idx, base_tag, model_id):
  tag = f"{base_tag}_{chunk_idx}"
  model_task_path = os.path.join(EOS_TMP_TASKS, model_id)

  if not os.path.exists(model_task_path):
    os.makedirs(model_task_path, exist_ok=True)
  input_f_bin = os.path.join(model_task_path, f"input-{tag}.bin")
  output_f_bin = os.path.join(model_task_path, f"output-{tag}.bin")
  try:
    write_smiles_bin(chunk, input_f_bin)
    cmd = f"bash {FRAMEWORK_FOLDER}/run.sh {FRAMEWORK_FOLDER} {input_f_bin} {output_f_bin} {ROOT}"
    subprocess.run(cmd, shell=True, check=True)
    if not os.path.exists(output_f_bin):
      raise FileNotFoundError(f"{output_f_bin} not found")
    results, header = read_bin(output_f_bin)
  finally:
    for fpath in [input_f_bin, output_f_bin]:
      if os.path.exists(fpath):
        os.remove(fpath)
  return results, header


def process_chunk(chunk, chunk_idx, base_tag, model_id, task_type):
  if task_type == "heavy":
    return _process_chunk_heavy(chunk, chunk_idx, base_tag, model_id)
  return _process_chunk_simple(chunk, chunk_idx, base_tag, model_id)


def fetch_cached_results(model_id, data):
  hash_key = f"cache:{model_id}"
  fields = [
    item["input"] if isinstance(item, dict) and "input" in item else item
    for item in data
  ]
  try:
    raw = redis_client.hmget(hash_key, fields)
  except Exception as e:
    logging.warning("Redis hmget failed: %s", e)
    return [], data
  results = []
  missing = []
  for item, val in zip(data, raw):
    if val:
      try:
        results.append(json.loads(val))
      except Exception:
        results.append(None)
    else:
      missing.append(item)
  return results, missing


def cache_missing_results(model_id, missing_inputs, computed_results):
  hash_key = f"cache:{model_id}"
  try:
    pipe = redis_client.pipeline()
    for item, result in zip(missing_inputs, computed_results):
      field = item.get("input") if isinstance(item, dict) and "input" in item else item
      pipe.hset(hash_key, field, json.dumps(result))
    pipe.expire(hash_key, REDIS_EXPIRATION)
    pipe.execute()
  except Exception as e:
    logging.warning("Redis cache save failed: %s", e)


def fetch_or_cache_header(model_id, computed_headers=None):
  header_key = f"{model_id}:header"
  cached = None
  try:
    cached = redis_client.get(header_key)
  except Exception as e:
    logging.warning("Redis get header failed: %s", e)
  if cached:
    try:
      return json.loads(cached) if isinstance(cached, str) else cached
    except Exception:
      return cached
  if computed_headers is not None:
    try:
      redis_client.setex(header_key, REDIS_EXPIRATION, json.dumps(computed_headers))
    except Exception as e:
      logging.warning("Redis setex header failed: %s", e)
    return computed_headers
  return None


def get_cached_or_compute(
  model_id,
  data,
  tag,
  max_workers,
  min_workers,
  metadata,
  fetch_cache=True,
  save_cache=True,
  cache_only=False,
  task_type="simple",
):
  hash_key = f"cache:{model_id}"

  if cache_only:
    fields = [
      item.get("input") if isinstance(item, dict) and "input" in item else item
      for item in data
    ]

    if fetch_cache:
      try:
        raw = redis_client.hmget(hash_key, fields)
      except Exception as e:
        logging.warning("Redis hmget in cache_only failed: %s", e)
        raw = [None] * len(fields)
    else:
      raw = [None] * len(fields)

    header = fetch_or_cache_header(model_id)
    if header is None:
      header, _ = load_csv_data(generic_example_output_file)

    results = []
    for val in raw:
      if val:
        try:
          results.append(json.loads(val))
        except Exception:
          results.append([None] * len(header))
      else:
        results.append([None] * len(header))
    return results, header

  if is_model_variable(metadata) or not init_redis():
    inputs = extract_input(data)
    return compute_results(inputs, tag, max_workers, min_workers, metadata, task_type)

  fields = [
    item.get("input") if isinstance(item, dict) and "input" in item else item
    for item in data
  ]

  if fetch_cache:
    try:
      raw = redis_client.hmget(hash_key, fields)
    except Exception as e:
      logging.warning("Redis hmget failed: %s", e)
      raw = [None] * len(fields)
  else:
    raw = [None] * len(fields)

  results = []
  missing = []
  for item, val in zip(data, raw):
    if val:
      try:
        results.append(json.loads(val))
      except Exception:
        results.append([None] * len(header))
    else:
      missing.append(item)

  computed_headers = None
  if missing:
    inputs = extract_input(missing)
    computed_results, computed_headers = compute_results(
      inputs, tag, max_workers, min_workers, metadata, task_type
    )
    results.extend(computed_results)

    if save_cache:
      cache_missing_results(model_id, missing, computed_results)

  header = fetch_or_cache_header(model_id, computed_headers)
  if header is None:
    header, _ = load_csv_data(generic_example_output_file)

  return results, header
