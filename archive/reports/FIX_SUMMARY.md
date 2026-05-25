# خلاصه مشکل و راه‌حل

**مشکل**: `CollectionManager(self.chroma_client)` → TypeError

**علت**: `CollectionManager.__init__(config_dir)` انتظار string دارد نه Client object

**راه‌حل**: باید در همه جا از `_create_collection_manager()` استفاده شود

**Locations to fix**:
- Line 196 در fallback exception handler
- Line 516 در _init_orchestrators
- Line 533 در answer_orchestrator

**Status**: در حال اصلاح...


