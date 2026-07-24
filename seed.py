from app.core.database import SessionLocal
from app.models.source import Source, SourceType
from app.models.entity import Entity, EntityType

db = SessionLocal()

s1 = Source(name="Times Of India", type=SourceType.news, identifier="https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms")
s2 = Source(name="Test Telegram Channel", type=SourceType.telegram, identifier="@testchannel")
db.add_all([s1, s2])
db.commit()

e1 = Entity(name="India", type=EntityType.org, aliases=["IN"])
e2 = Entity(name="Testing 1", type=EntityType.person, aliases=[])
db.add_all([e1, e2])
db.commit()

print("Seeded:", s1.id, s2.id, e1.id, e2.id)
db.close()

s = Source(name="BBC World", type=SourceType.news, identifier="http://feeds.bbci.co.uk/news/world/rss.xml", is_active=True)
db.add(s)
db.commit()

s = Source(name="BBC News", type=SourceType.telegram, identifier="@bbcnews", is_active=True)
db.add(s)
db.commit()