import time
import functools

def retry_stage(max_attempts: int = 3, backoff_seconds: float = 1.5):
    """
    Wraps a stage function. Retries on any exception, with exponential backoff.
    Each stage gets its OWN retry budget — a flaky classification call doesn't
    consume or affect NER's retry attempts, and vice versa.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    print(f"[{fn.__name__}] attempt {attempt}/{max_attempts} failed: {e}")
                    if attempt < max_attempts:
                        time.sleep(backoff_seconds * attempt)
            raise last_exception
        return wrapper
    return decorator