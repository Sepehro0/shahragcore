# مشکل: `pattern_handler` attribute نیست

سیستم از `UltimateRAGSystem` به عنوان parent استفاده می‌کند و orchestrator ها به درستی فعال نیستند.

## راه‌حل سریع:

باید orchestrator ها را به طور کامل فعال کنیم تا از path parent استفاده نکنیم.

فعلاً orchestrator ها disabled هستند و همه چیز داره به parent delegate میشه که اون attribute هایی مثل `pattern_handler` نداره.

باید orchestrators را FORCE ENABLE کنیم در `_init_orchestrators()`.

خطا در:
- `ultimate_rag_system.py` line 4143 → `self.normalize_text(query)`
- این به `refactored_rag_system.py` → `self.text_normalizer.normalize_text(text)`  
- که بعد به `__getattr__` → `self._parent_system.text_normalizer`
- ولی parent این attribute رو نداره!

## Fix:

باید orchestrator ها رو enable کنیم با تمام dependencies خودشون، نه delegate به parent.


