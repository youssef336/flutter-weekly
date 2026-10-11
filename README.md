# Flutter Weekly

موقع بسيط (HTML + CSS + JavaScript) بيتابع قناة يوتيوب الرسمية لـ Flutter
([@flutterdev](https://www.youtube.com/@flutterdev/videos)) ويعرض:

- **ملخص الأسبوع**: عدد الفيديوهات، المشاهدات، أكتر المواضيع، وسطر لكل فيديو — وتقدر ترجع للأسابيع اللي فاتت.
- **كل الفيديوهات**: كروت بالصورة والتاريخ والملخص، مع فلتر بالتصنيف وبحث.

## بيشتغل إزاي

- `scripts/fetch.py` (Python بدون مكتبات خارجية) بيقرا RSS القناة، بيطلع ملخص قصير من وصف كل فيديو
  ويصنفه، ويدمجه في `data/videos.json` (القديم بيفضل محفوظ).
- `.github/workflows/update.yml` بيشغّل السكريبت كل يوم الساعة 6 الصبح UTC ويعمل commit لو فيه جديد.
- الموقع static على GitHub Pages وبيقرا `data/videos.json`.

> الملخص مأخوذ من وصف الفيديو على يوتيوب، فهو بالإنجليزي زي الوصف الأصلي.

## تشغيل local

```bash
python3 scripts/fetch.py        # تحديث البيانات
python3 -m http.server 8000     # وافتح http://localhost:8000
```
