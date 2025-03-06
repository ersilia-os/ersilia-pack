from uuid import uuid4

from fastapi import Request


class RequestContextMiddleware:
  def __init__(self, app):
    self.app = app

  async def __call__(self, scope, receive, send):
    if scope["type"] != "http":
      return await self.app(scope, receive, send)

    request = Request(scope, receive)
    request_id = str(uuid4())
    request.state.request_id = request_id

    async def send_wrapper(message):
      if message["type"] == "http.response.start":
        headers = message.setdefault("headers", [])
        headers.append((b"x-request-id", request_id.encode("latin-1")))
      await send(message)

    await self.app(scope, receive, send_wrapper)
