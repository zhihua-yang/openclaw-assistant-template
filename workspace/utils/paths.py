import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DIR = os.path.join(BASE_DIR, "memory")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

CAPABILITIES_JSON     = os.path.join(MEMORY_DIR, "capabilities.json")
ANTIPATTERNS_JSON     = os.path.join(MEMORY_DIR, "antipatterns.json")
INTELLIGENCE_INDEX    = os.path.join(MEMORY_DIR, "intelligence_index.json")
EVOLUTION_CHAIN       = os.path.join(MEMORY_DIR, "evolution_chain.jsonl")
AUDIT_QUEUE           = os.path.join(MEMORY_DIR, "audit_queue.jsonl")
PROFILE_JSON          = os.path.join(MEMORY_DIR, "profile.json")
GOALS_JSON            = os.path.join(MEMORY_DIR, "goals.json")
WEEKLY_SUMMARY        = os.path.join(MEMORY_DIR, "weekly_summary.json")
RECENT_DIGEST         = os.path.join(MEMORY_DIR, "recent_digest.json")
TRAINING_PLAN         = os.path.join(MEMORY_DIR, "training_plan.json")
CALIBRATION           = os.path.join(MEMORY_DIR, "calibration.json")
