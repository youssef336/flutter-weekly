"""Write Arabic AI summaries into data/videos.json with the Gemini API.

Per video: Gemini watches the YouTube video from its URL (falls back to the
title + description if it can't) and returns {about, points, verdict}.
Per week (Saturday -> Friday, Cairo time): one digest over that week's video
summaries, regenerated whenever the week's set of videos changes.

Needs GEMINI_API_KEY in the environment; without it the script does nothing.
Standard library only.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'videos.json'
API = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
# First model the key can use wins. Override with GEMINI_MODEL.
MODELS = [m for m in [os.environ.get('GEMINI_MODEL'), 'gemini-3-flash-preview',
                      'gemini-3-flash', 'gemini-2.5-flash'] if m]
CAIRO = ZoneInfo('Africa/Cairo')
MAX_VIDEOS_PER_RUN = 10
PAUSE_SECONDS = 8  # stay well under the free-tier requests-per-minute limit

# Bump when the writing style changes: summaries with an older style get rewritten.
STYLE_VERSION = 2
STYLE = (
    'اكتب بالعربي المصري البسيط، كأنك بتشرح لصاحبك اللي لسه junior في Flutter وبادئ قريب. '
    'سيب أسماء الـ APIs والـ packages والمصطلحات بالإنجليزي زي ما هي، بس أول مرة يظهر مصطلح '
    'مش أساسي اشرحه بين قوسين في كلمتين بسيطين، مثلاً: Impeller (المحرك اللي بيرسم الشاشة). '
    'استخدم جمل قصيرة، وقول الفايدة العملية: الحاجة دي بتفرق معاك في إيه. '
    'لو فيه مثال بسيط من الحياة يوضح الفكرة استخدمه. من غير مقدمات أو مجاملات، '
    'ومتألفش أي معلومة مش موجودة.'
)

VIDEO_PROMPT = STYLE + '''
لخّص فيديو قناة Flutter الرسمية ده. العنوان: "{title}".
- about: جملة واحدة الفيديو بيتكلم عن إيه.
- points: من 3 لـ 5 نقط بأهم الحاجات اللي اتقالت (للـ Short من 1 لـ 3). كل نقطة جملة قصيرة فيها معلومة حقيقية من الفيديو.
- verdict: سطر واحد: يهمك لو إيه، ومحتاج تتفرج عليه بنفسك ولا الملخص كفاية.
- terms: من 0 لـ 3 مصطلحات تقنية من الفيديو ممكن junior ميعرفهاش، كل واحد term بالإنجليزي و meaning جملة بسيطة بالعربي.'''

DESCRIPTION_PROMPT = STYLE + '''
مش متاح الفيديو نفسه، فلخّص من العنوان والوصف بس، ومتألفش حاجة مش مكتوبة.
العنوان: "{title}"
الوصف:
{description}
- about: جملة واحدة الفيديو بيتكلم عن إيه.
- points: من 2 لـ 4 نقط من اللي في الوصف.
- verdict: سطر واحد: يهمك لو إيه.
- terms: من 0 لـ 3 مصطلحات تقنية ممكن junior ميعرفهاش، term بالإنجليزي و meaning جملة بسيطة بالعربي.'''

WEEK_PROMPT = STYLE + '''
دي ملخصات فيديوهات قناة Flutter الرسمية في أسبوع واحد:
{videos}
- digest: فقرة من 3 لـ 5 جمل تقول أهم اللي حصل في Flutter الأسبوع ده كأنك بتحكيه لزميل.
- highlights: من 2 لـ 4 نقط بأهم الحاجات العملية (إصدارات، features، أدوات) اللي تستاهل تعرفها.'''

VIDEO_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'about': {'type': 'STRING'},
        'points': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
        'verdict': {'type': 'STRING'},
        'terms': {
            'type': 'ARRAY',
            'items': {
                'type': 'OBJECT',
                'properties': {'term': {'type': 'STRING'}, 'meaning': {'type': 'STRING'}},
                'required': ['term', 'meaning'],
            },
        },
    },
    'required': ['about', 'points', 'verdict', 'terms'],
}

WEEK_SCHEMA = {
    'type': 'OBJECT',
    'properties': {
        'digest': {'type': 'STRING'},
        'highlights': {'type': 'ARRAY', 'items': {'type': 'STRING'}},
    },
    'required': ['digest', 'highlights'],
}


class QuotaExceeded(Exception):
    pass


class Gemini:
    def __init__(self, key):
        self.key = key
        self.models = list(MODELS)

    def generate(self, parts, schema, video=False):
        config = {'responseMimeType': 'application/json', 'responseSchema': schema}
        if video:
            config['mediaResolution'] = 'MEDIA_RESOLUTION_LOW'  # ~3x fewer tokens per second of video
        body = json.dumps({'contents': [{'parts': parts}], 'generationConfig': config}).encode()
        busy_retries = 3
        while self.models:
            request = urllib.request.Request(
                API.format(model=self.models[0]), data=body, method='POST',
                headers={'Content-Type': 'application/json', 'x-goog-api-key': self.key})
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    data = json.loads(response.read())
                text = data['candidates'][0]['content']['parts'][0]['text']
                return json.loads(text)
            except urllib.error.HTTPError as err:
                detail = err.read().decode(errors='replace')[:300]
                if err.code == 404:
                    print(f'  model {self.models[0]} not available, trying the next one')
                    self.models.pop(0)
                    continue
                if err.code == 429:
                    raise QuotaExceeded(detail)
                if err.code in (500, 503) and busy_retries:  # "high demand" spikes are short
                    busy_retries -= 1
                    print(f'  Gemini busy (HTTP {err.code}), retrying in 30s')
                    time.sleep(30)
                    continue
                raise RuntimeError(f'HTTP {err.code}: {detail}')
        raise RuntimeError('no Gemini model available for this key')


def watch_url(video):
    return f"https://www.youtube.com/watch?v={video['id']}"


def summarize_video(gemini, video):
    try:
        ai = gemini.generate(
            [{'file_data': {'file_uri': watch_url(video)}},
             {'text': VIDEO_PROMPT.format(title=video['title'])}],
            VIDEO_SCHEMA, video=True)
        ai['source'] = 'video'
    except QuotaExceeded:
        raise
    except Exception as err:  # video too long, unavailable, … -> use the description
        print(f'  video failed ({err}), falling back to the description')
        time.sleep(PAUSE_SECONDS)
        ai = gemini.generate(
            [{'text': DESCRIPTION_PROMPT.format(
                title=video['title'], description=video.get('description', ''))}],
            VIDEO_SCHEMA)
        ai['source'] = 'description'
    ai['model'] = gemini.models[0]
    ai['style'] = STYLE_VERSION
    return ai


def is_current(video):
    return video.get('ai', {}).get('style') == STYLE_VERSION


def week_key(published):
    local = datetime.fromisoformat(published).astimezone(CAIRO)
    start = local - timedelta(days=(local.weekday() - 5) % 7)  # weekday(): Sat = 5
    return start.date().isoformat()


def summarize_weeks(gemini, data):
    by_week = {}
    for video in data['videos']:
        by_week.setdefault(week_key(video['published']), []).append(video)
    weeks = data.setdefault('weeks', {})
    for key, videos in sorted(by_week.items(), reverse=True):
        if not all(is_current(v) for v in videos):
            continue  # wait until every video of the week has its own up-to-date summary
        ids = sorted(v['id'] for v in videos)
        week = weeks.get(key, {})
        if week.get('ids') == ids and week.get('style') == STYLE_VERSION:
            continue
        print(f'week {key}: {len(videos)} videos')
        listing = '\n'.join(
            f"- {v['title']}: {v['ai']['about']} " + ' '.join(v['ai']['points'])
            for v in sorted(videos, key=lambda v: v['published']))
        result = gemini.generate([{'text': WEEK_PROMPT.format(videos=listing)}], WEEK_SCHEMA)
        weeks[key] = {'ids': ids, 'style': STYLE_VERSION, **result}
        save(data)
        time.sleep(PAUSE_SECONDS)


def save(data):
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', 'utf-8')


def main():
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        print('GEMINI_API_KEY is not set, skipping AI summaries')
        return
    gemini = Gemini(key)
    data = json.loads(DATA_FILE.read_text('utf-8'))
    # Never-summarized videos first, then rewrite ones in an older style; newest first in each.
    missing = [v for v in data['videos'] if 'ai' not in v]
    outdated = [v for v in data['videos'] if 'ai' in v and not is_current(v)]
    pending = (missing + outdated)[:MAX_VIDEOS_PER_RUN]
    try:
        for video in pending:
            print(f"video {video['id']}: {video['title']}")
            video['ai'] = summarize_video(gemini, video)
            save(data)  # keep progress if a later call fails
            time.sleep(PAUSE_SECONDS)
        summarize_weeks(gemini, data)
    except QuotaExceeded as err:
        print(f'quota reached, the rest waits for the next run: {err}')
    except RuntimeError as err:
        print(f'stopping: {err}')
        sys.exit(1)


if __name__ == '__main__':
    main()
