from tracardi.event_server.utils.memory_cache import CacheItem
from tracardi.domain.event import Event
from tracardi.service.storage.driver import storage
from tracardi.config import memory_cache
from tracardi.domain.event_tag import EventTag


def tags_service(event: Event):
    if "tags-type-{}".format(event.type) not in memory_cache:
        result = list(await storage.driver.tag.get_by_type(event.type)).pop()
        memory_cache["tags-type-{}".format(event.type)] = CacheItem(
            data=EventTag(**result).tags,
            ttl=memory_cache.tags_ttl
        )
    event.tags = memory_cache["tags-type-{}".format(event.type)].data
    return event
