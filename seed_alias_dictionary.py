from app.core.database import SessionLocal
from app.models.entity_alias_dictionary import EntityAliasDictionary
from app.services.entity_resolver import normalize_name

db = SessionLocal()

SEED_ALIASES = [
    ("People's Liberation Army", ["PLA", "PLA Army", "People's Liberation Army", "中国人民解放军", "Chinese PLA"]),
    ]

for canonical, aliases in SEED_ALIASES:
    for alias in aliases:
        normalized = normalize_name(alias)
        exists = db.query(EntityAliasDictionary).filter(
            EntityAliasDictionary.alias_normalized == normalized
        ).first()
        if not exists:
            db.add(EntityAliasDictionary(canonical_name=canonical, alias_normalized=normalized))

db.commit()
print("Alias dictionary seeded")