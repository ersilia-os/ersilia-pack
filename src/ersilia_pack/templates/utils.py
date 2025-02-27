import asyncio, collections, csv, os, subprocess, psutil, multiprocessing, json
from redis import Redis, ConnectionError
from slowapi import Limiter
from slowapi.util import get_remote_address

from .default import (
  ENVIRONMENT,
  EXAMPLE_INPUT_PATH,
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
)


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


def orient_to_json(values, columns, index, orient, output_type):
  if len(output_type) > 1:
    output_type = "string"
  else:
    output_type = output_type[0].lower()

  def values_serializer(values):
    if output_type == "string":
      return [str(x) for x in values]
    if output_type == "float":
      return [None if x.strip() == "" else float(x) for x in values]
    elif output_type == "integer":
      return [None if x.strip() == "" else int(x) for x in values]
    return values

  if orient == "split":
    data = collections.OrderedDict()
    data["columns"] = columns
    data["index"] = index
    data["data"] = values_serializer(values)
    return data

  if orient == "records":
    data = []
    for i in range(len(values)):
      record = collections.OrderedDict()
      for j in range(len(columns)):
        record[columns[j]] = values_serializer([values[i][j]])[0]
      data += [record]
    return data

  if orient == "index":
    data = collections.OrderedDict()
    for i in range(len(index)):
      record = collections.OrderedDict()
      for j in range(len(columns)):
        record[columns[j]] = values_serializer([values[i][j]])[0]
      data[index[i]] = record
    return data

  if orient == "columns":
    data = collections.OrderedDict()
    for j in range(len(columns)):
      records = collections.OrderedDict()
      for i in range(len(index)):
        records[index[i]] = values_serializer([values[i][j]])[0]
      data[columns[j]] = records
    return data

  elif orient == "values":
    return values_serializer(values)

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
  except ConnectionError:
    redis_client = None
    print("Redis not connected")
    return False


async def load_card_metadata(bundle_folder: str):
  file_path = os.path.join(bundle_folder, "information.json")
  contents = await asyncio.to_thread(_read_file, file_path)
  return json.loads(contents)


def _read_file(file_path: str) -> str:
  with open(file_path, "r") as f:
    return f.read()


async def get_metadata():
  data = await load_card_metadata(BUNDLE_FOLDER)
  return data["card"]


def read_example():
  if not os.path.exists(EXAMPLE_INPUT_PATH):
    print("Examplery input. Path is not existed")
    return []

  with open(EXAMPLE_INPUT_PATH, "r") as f:
    reader = csv.reader(f)
    next(reader)
    data = [x[0] for x in reader]
  return data


def load_csv_data(file_path: str):
  with open(file_path, "r") as f:
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
  except ConnectionError:
    raise ConnectionError("Redis is not initialized!")

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
  model_size_byte = get_model_dir_size(MODEL_ROOT)
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


def run_in_parallel(num_workers, timeout, tag, chunks):
  with multiprocessing.Pool(processes=num_workers) as pool:
    chunk_args = [(chunk, idx, tag) for idx, chunk in enumerate(chunks)]
    processed = pool.starmap_async(process_chunk, chunk_args)
    _results = processed.get(timeout=timeout)
    results, headers = [], []
    for result, header in _results:
      results.extend(result)
      headers.append(header)
  return results, headers[0]


def compute_parallel(data, tag, timeout, max_workers, min_workers):
  num_workers = compute_num_workers(data, max_workers, min_workers)
  chunks = split_data(data, num_workers)
  return run_in_parallel(num_workers, timeout, tag, chunks)


def run_sequential_data(tag, data):
  return process_chunk(data, 0, tag)


def is_parallel_amenable(data):
  model_size_byte = get_model_dir_size(MODEL_ROOT)
  model_size_thres = compute_max_model_size_threshold()
  if model_size_byte > model_size_thres and len(data) >= int(DATA_SIZE_LOWERBOUND):
    return True
  elif model_size_byte < model_size_thres and len(data) >= int(DATA_SIZE_UPPERBOUND):
    return True
  return False


def compute_results(data, tag, timeout, max_workers, min_workers):
  parallel_amenable = is_parallel_amenable(data)
  if parallel_amenable:
    return compute_parallel(data, tag, timeout, max_workers, min_workers)
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
  result_keys = [f"{model_id}:{item['key']}" for item in data]
  cached_results = redis_client.mget(result_keys)
  results = []
  missing_inputs = []

  for item, cached in zip(data, cached_results):
    if cached:
      results.append(json.loads(cached))
    else:
      missing_inputs.append(item)

  return results, missing_inputs


def cache_missing_results(model_id, missing_inputs, computed_results):
  for item, result in zip(missing_inputs, computed_results):
    result_key = f"{model_id}:{item['key']}"
    redis_client.setex(result_key, REDIS_EXPIRATION, json.dumps(result))


def fetch_or_cache_header(model_id, computed_headers=None):
  header_key = f"{model_id}:header"
  cached_header = redis_client.mget(header_key)[0]

  if cached_header:
    cached_header
    return (
      json.loads(cached_header) if isinstance(cached_header, str) else cached_header
    )
  elif computed_headers:
    redis_client.setex(header_key, REDIS_EXPIRATION, json.dumps(computed_headers))
    return computed_headers
  return None


def get_cached_or_compute(model_id, data, tag, timeout, max_workers, min_workers):
  if not input_has_key(data):
    inputs = extract_input(data)
    return compute_results(inputs, tag, timeout, max_workers, min_workers)

  if not init_redis():
    inputs = extract_input(data)
    return compute_results(inputs, tag, timeout, max_workers, min_workers)

  results, missing_inputs = fetch_cached_results(model_id, data)
  computed_headers = None

  if missing_inputs:
    inputs = extract_input(missing_inputs)
    computed_results, computed_headers = compute_results(
      inputs, tag, timeout, max_workers, min_workers
    )
    cache_missing_results(model_id, missing_inputs, computed_results)
    results.extend(computed_results)
  header = fetch_or_cache_header(model_id, computed_headers)
  return results, header
