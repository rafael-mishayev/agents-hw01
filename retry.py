import time

from openai import APIConnectionError, InternalServerError, RateLimitError

# Temporary failures worth retrying: 429 (rate limit), 5xx (e.g. 503 overloaded), network errors.
# APITimeoutError is a subclass of APIConnectionError.
RETRYABLE = (RateLimitError, InternalServerError, APIConnectionError)

MAX_TRIES = 4  # 1 call + up to 3 retries
WAIT_SECONDS = [3, 8, 15]  # wait before retry 1, 2, 3


def call_with_retry(fn, *args, **kwargs):
    """Call fn(*args, **kwargs); retry only on temporary API failures.

    If all tries fail, the last exception is raised. Retries happen at the network
    level and are NOT counted as generation attempts of the Actor-Critic loop.
    """
    for i in range(MAX_TRIES):
        try:
            return fn(*args, **kwargs)
        except RETRYABLE as e:
            if i == MAX_TRIES - 1:
                raise
            wait = WAIT_SECONDS[i]
            print(f"[retry] {type(e).__name__}, waiting {wait}s (retry {i + 1}/{MAX_TRIES - 1})", flush=True)
            time.sleep(wait)
