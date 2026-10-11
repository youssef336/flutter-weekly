# Flutter Weekly

موقع بسيط (HTML + CSS + JavaScript) بيتابع قناة يوتيوب الرسمية لـ Flutter
([@flutterdev](https://www.youtube.com/@flutterdev/videos)) ويعرض:

- **ملخص الأسبوع**: عدد الفيديوهات، المشاهدات، أكتر المواضيع، وسطر لكل فيديو — وتقدر ترجع للأسابيع اللي فاتت.
- **كل الفيديوهات**: كروت بالصورة والتاريخ والملخص، مع فلتر بالتصنيف وبحث.

## بيشتغل إزاي

- `scripts/fetch.py` (Python بدون مكتبات خارجية) بيقرا RSS القناة، بيطلع ملخص قصير من وصف كل فيديو
  ويصنفه، ويدمجه في `data/videos.json` (القديم بيفضل محفوظ).
- `scripts/summarize.py` بيبعت كل فيديو جديد لـ **Gemini** (بيتفرج على الفيديو من لينك يوتيوب) ويكتب ملخص بالعربي:
  الفيديو عن إيه، 3–5 نقط بأهم اللي اتقال، ويهمك ولا لأ. وبعدين بيكتب ملخص لكل أسبوع.
  لو الفيديو منفعش، بيلخص من الوصف وبيكتب كده جنب الملخص.
- `.github/workflows/update.yml` بيشغّل الاتنين كل يوم الساعة 8 الصبح UTC ويعمل commit لو فيه جديد.
- الموقع static على GitHub Pages وبيقرا `data/videos.json`.

## مفتاح Gemini

خد مفتاح مجاني من [Google AI Studio](https://aistudio.google.com/apikey) وحطه كـ secret:

```bash
gh secret set GEMINI_API_KEY -R youssef336/flutter-weekly
```

ولو عايز موديل معين: `gh variable set GEMINI_MODEL -R youssef336/flutter-weekly --body gemini-2.5-flash`

## تشغيل local

```bash
python3 scripts/fetch.py        # تحديث البيانات
GEMINI_API_KEY=... python3 scripts/summarize.py   # الملخصات
python3 -m http.server 8000     # وافتح http://localhost:8000
```
