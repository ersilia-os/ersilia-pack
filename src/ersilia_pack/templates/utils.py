import asyncio, csv, os, subprocess, psutil, multiprocessing, json, redis
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
  generic_example_input_file,
)


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
  print(f"Output type: {output_type}")
  if len(output_type) > 1:
    output_type = "string"
  else:
    output_type = output_type[0].lower()

  def convert_value(x):
    if x == "" or x is None:
      return None
    if output_type == "string":
      return str(x)
    if output_type == "float":
      if isinstance(x, list) and x:
        x = x[0]
      try:
        return float(x)
      except (ValueError, TypeError):
        return None
    if output_type == "integer":
      if isinstance(x, list) and x:
        x = x[0]
      try:
        return int(x)
      except (ValueError, TypeError):
        try:
          f = float(x)
        except (ValueError, TypeError):
          return None
        if f.is_integer():
          return int(f)
        return int(f)
    return x

  if values and isinstance(values[0], list):
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
    print("Redis connected")
    return True
  except redis.ConnectionError:
    redis_client = None
    print("Redis not connected")
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


def resource_planner(data, max_workers):
  mem_size = int(available_mem() * RESOURCE_SAFETY_MARGIN)
  max_workers_memory = max(1, int(mem_size // model_size_byte))
  cpu_count = get_cpu_count(False)
  data_constraint = len(data) if len(data) > 0 else 1
  num_workers = min(max_workers, max_workers_memory, cpu_count, data_constraint)
  return num_workers


def compute_num_workers(data, max_workers, min_workers):
  num_workers = resource_planner(data, max_workers)
  num_workers = max(num_workers, min_workers)
  return num_workers


def available_mem():
  return psutil.virtual_memory().available


def available_mem_total():
  return psutil.virtual_memory().total


def get_cpu_count(logical):
  return psutil.cpu_count(logical=logical)


def run_in_parallel(num_workers, tag, chunks):
  num_tasks = len(chunks)
  chunksize = max(1, num_tasks // (num_workers * 2))
  print(f"Chunk size: {chunksize} | number worker: {num_workers}")

  with multiprocessing.Pool(processes=num_workers) as pool:
    chunk_args = [(chunk, idx, tag) for idx, chunk in enumerate(chunks)]
    async_result = pool.starmap_async(process_chunk, chunk_args, chunksize=chunksize)
    results_headers = async_result.get()

  results, headers = [], []
  for result, header in results_headers:
    results.extend(result)
    headers.append(header)

  return results, headers[0]


def compute_parallel(data, tag, max_workers, min_workers):
  num_workers = compute_num_workers(data, max_workers, min_workers)
  os.environ["MAX_WORKERS"] = str(num_workers)
  chunks = split_data(data, num_workers)
  return run_in_parallel(num_workers, tag, chunks)


def run_sequential_data(tag, data):
  return process_chunk(data, 0, tag)


def is_model_variable(metadata):
  if OUTPUT_CONSISTENCY in metadata:
    if metadata[OUTPUT_CONSISTENCY] == "Variable":
      return True
  if "Generative" in metadata["Task"]:
    return True
  return False


def is_parallel_amenable(data, metadata):
  model_size_thres = compute_max_model_size_threshold()
  if is_model_variable(metadata):
    return True
  if model_size_byte > model_size_thres and len(data) >= int(DATA_SIZE_LOWERBOUND):
    return True
  elif model_size_byte < model_size_thres and len(data) >= int(DATA_SIZE_UPPERBOUND):
    return True
  return False


def compute_results(data, tag, max_workers, min_workers, metadata):
  parallel_amenable = is_parallel_amenable(data, metadata)
  print(f"Amenable for multiprocessing: {parallel_amenable}")
  if parallel_amenable:
    return compute_parallel(data, tag, max_workers, min_workers)
  else:
    return run_sequential_data(tag, data)


def process_chunk(chunk, chunk_idx, base_tag):
  tag = f"{base_tag}_{chunk_idx}"
  input_f = os.path.join(TEMP_FOLDER, f"input-{tag}.csv")
  output_f = os.path.join(TEMP_FOLDER, f"output-{tag}.csv")
  try:
    with open(input_f, "w", newline="") as csvfile:
      writer = csv.writer(csvfile)
      writer.writerow(["input"])
      for item in chunk:
        writer.writerow([item])

    cmd = (
      f"bash {FRAMEWORK_FOLDER}/run.sh {FRAMEWORK_FOLDER} {input_f} {output_f} {ROOT}"
    )
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


def fetch_cached_results(model_id, data):
  hash_key = f"cache:{model_id}"
  fields = [item["input"] if "input" in item else item for item in data]
  raw = redis_client.hmget(hash_key, fields)
  results = []
  missing = []
  for item, val in zip(data, raw):
    if val:
      results.append(json.loads(val))
    else:
      missing.append(item)
  return results, missing


def cache_missing_results(model_id, missing_inputs, computed_results):
  hash_key = f"cache:{model_id}"
  pipe = redis_client.pipeline()
  for item, result in zip(missing_inputs, computed_results):
    field = item["input"] if "input" in item else item
    pipe.hset(hash_key, field, json.dumps(result))
  pipe.expire(hash_key, REDIS_EXPIRATION)
  pipe.execute()


def fetch_or_cache_header(model_id, computed_headers=None):
  header_key = f"{model_id}:header"
  cached = redis_client.get(header_key)
  if cached:
    return json.loads(cached) if isinstance(cached, str) else cached
  if computed_headers:
    redis_client.setex(header_key, REDIS_EXPIRATION, json.dumps(computed_headers))
    return computed_headers
  return None


def get_cached_or_compute(model_id, data, tag, max_workers, min_workers, metadata):
  if is_model_variable(metadata) or not init_redis():
    inputs = extract_input(data)
    return compute_results(inputs, tag, max_workers, min_workers, metadata)
  results, missing = fetch_cached_results(model_id, data)
  computed_headers = None
  if missing:
    inputs = extract_input(missing)
    computed_results, computed_headers = compute_results(
      inputs, tag, max_workers, min_workers, metadata
    )
    cache_missing_results(model_id, missing, computed_results)
    results.extend(computed_results)
  header = fetch_or_cache_header(model_id, computed_headers)
  return results, header
