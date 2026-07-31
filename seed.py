from app.core.database import SessionLocal
from app.models.source import Source, SourceType, Language

db = SessionLocal()

TOPICS = {
    "military_news": "Indian Defence News OR military operations",
    "geopolitical_topics": "geopolitical conflicts OR border disputes OR regional conflicts",
}

LANG_CONFIG = {
    "en": {"hl": "en-US", "gl": "US", "ceid": "US:en"},
    "ur": {"hl": "ur-PK", "gl": "PK", "ceid": "PK:ur"},
    "zh": {"hl": "zh-CN", "gl": "CN", "ceid": "CN:zh-Hans"},
}

sources = []

for topic_key, query in TOPICS.items():
    for lang, cfg in LANG_CONFIG.items():
        url = (
            f"https://news.google.com/rss/search?q={query.replace(' ', '+')}"
            f"&hl={cfg['hl']}&gl={cfg['gl']}&ceid={cfg['ceid']}"
        )

        telegram_sources = [
            Source(
                name="World MilitaryNews",
                type=SourceType.telegram,
                identifier="@WOR_MIL_NEWS",
                is_active=True,
            ),
            Source(
                name="GEOPOLITICAL DISCUSSION",
                type=SourceType.telegram,
                identifier="@GEOPOLITICAL_DISCUSSION",
                is_active=True,
            ),
           
        ]
        sources.append(Source(
            name=f"Google News [{lang}] - {topic_key}",
            type=SourceType.news,
            identifier=url,
            language=Language(lang),
            topic=topic_key,
            is_active=True,
        ))


direct_feeds = [
    ("BBC news (Urdu)", "https://rss.app/feeds/5so5OYcyWxi3hqNj.xml", "ur", "military_news"),
    ("Google news (English)", "https://rss.app/feeds/ilGaY3FoZNQVyKNo.xml", "en", "military_news"),
    ("Google news (Chinese)", "https://rss.app/feeds/JPJ8EKTkeyBVJ0vh.xml", "zh", "military_news"),
     
    ("BBC news (Urdu)", "https://rss.app/feeds/ZetDegJHKZqARgiw.xml", "ur", "geopolitical_topics"),
    ("Google news (English)", "https://rss.app/feeds/0HVMDogUYcAsUwvi.xml", "en", "geopolitical_topics"),
    ("Google news (Chinese)", "https://rss.app/feeds/kLC6l8gIYjhmFYmV.xml", "zh", "geopolitical_topics   "),
]
for name, url, lang, topic in direct_feeds:
    sources.append(Source(
        name=name, type=SourceType.news, identifier=url,
        language=Language(lang), topic=topic, is_active=True,
    ))

db.add_all(sources)
db.commit()
print(f"Seeded {len(sources)} news sources")