import logging


def log_cache_event(
    logger,
    *,
    component,
    action,
    cache_key,
    language_code=None,
    timeout=None,
    detail=None,
):
    parts = [f"component={component}", f"action={action}", f"key={cache_key}"]
    if language_code:
        parts.append(f"lang={language_code}")
    if timeout is not None:
        parts.append(f"timeout={timeout}")
    if detail:
        parts.append(f"detail={detail}")
    logger.info("CACHE %s", " ".join(parts))


def get_cache_logger(name):
    return logging.getLogger(f"cache.{name}")
