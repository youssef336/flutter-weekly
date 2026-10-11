"""Fetch the Flutter YouTube channel RSS feed and merge it into data/videos.json.

Standard library only. The feed returns just the latest 15 videos, so older
entries already in videos.json are kept and only updated when they reappear.
"""

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

CHANNEL_ID = 'UCwXdFgeE9KYzlDdR7TG9cMw'  # youtube.com/@flutterdev
FEED_URL = f'https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}'
DATA_FILE = Path(__file__).resolve().parent.parent / 'data' / 'videos.json'

NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'yt': 'http://www.youtube.com/xml/schemas/2015',
    'media': 'http://search.yahoo.com/mrss/',
}

# (tag id, regex over title + description). First match order = display order.
TAGS = [
    ('release', r'\bflutter \d+\.\d+|\bdart \d+\.\d+|what.?s new|release|announc'),
    ('dart', r'\bdart\b'),
    ('ai', r'\bgemini\b|\bai\b|\bagent|\bmcp\b|genkit|firebase ai|llm'),
    ('widget', r'widget of the week|\bwidgets?\b'),
    ('observable', r'observable flutter'),
    ('tutorial', r'how to|tutorial|codelab|getting started|deep dive|explained|of the week|breaks down'),
    ('event', r'fluttercon|google i/o|\bi/o\b|cloud next|keynote|conference'),
    ('community', r'community|interview|sits down|catches up|story|showcase|case study|switched to'),
    ('performance', r'performance|jank|impeller|profil|devtools'),
    ('web', r'flutter web|\bweb platform|wasm|webassembly'),
    ('games', r'\bgame|flame\b|casual games'),
]

NOISE_LINE = re.compile(
    r'^(subscribe|watch more|resources?:|chapters?:|products mentioned|speakers?:|'
    r'follow|learn more|check out|#)',
    re.IGNORECASE,
)


def clean_paragraph(paragraph):
    lines = []
    for line in paragraph.splitlines():
        line = line.strip()
        # Skip "Label → link" rows, chapter timestamps and boilerplate footers.
        if '→' in line or NOISE_LINE.match(line) or re.match(r'^\d{1,2}:\d{2}', line):
            continue
        line = re.sub(r'https?://\S+', '', line)
        line = re.sub(r'#\w+', '', line).strip()
        if line:
            lines.append(line)
    return re.sub(r'\s+', ' ', ' '.join(lines)).strip()


def clean_summary(description, max_sentences=3, max_chars=320):
    paragraphs = [clean_paragraph(p) for p in re.split(r'\n\s*\n', description)]
    paragraphs = [p for p in paragraphs if p]
    # First paragraph that reads like prose, else whatever is left.
    text = next((p for p in paragraphs if len(p) >= 40), paragraphs[0] if paragraphs else '')
    sentences = re.split(r'(?<=[.!?])\s+', text)
    summary = ' '.join(sentences[:max_sentences]).strip()
    if len(summary) > max_chars:
        summary = summary[:max_chars].rsplit(' ', 1)[0] + '…'
    return summary


def tags_for(title, summary, is_short):
    haystack = f'{title}\n{summary}'.lower()
    tags = [tag for tag, pattern in TAGS if re.search(pattern, haystack)]
    if is_short:
        tags.insert(0, 'shorts')
    return tags[:4]


def parse_feed(xml_text):
    root = ET.fromstring(xml_text)
    videos = []
    for entry in root.findall('atom:entry', NS):
        video_id = entry.findtext('yt:videoId', default='', namespaces=NS)
        title = entry.findtext('atom:title', default='', namespaces=NS).strip()
        link = entry.find('atom:link', NS).get('href', '')
        group = entry.find('media:group', NS)
        description = group.findtext('media:description', default='', namespaces=NS)
        thumb = group.find('media:thumbnail', NS)
        stats = group.find('media:community/media:statistics', NS)
        is_short = '/shorts/' in link
        summary = clean_summary(description)
        videos.append({
            'id': video_id,
            'title': title,
            'url': link or f'https://www.youtube.com/watch?v={video_id}',
            'published': entry.findtext('atom:published', default='', namespaces=NS),
            'thumbnail': thumb.get('url') if thumb is not None else '',
            'views': int(stats.get('views', 0)) if stats is not None else 0,
            'isShort': is_short,
            'summary': summary,
            # Tag on title + summary only: footers (dart.dev links, "Live from…") are noise.
            'tags': tags_for(title, summary, is_short),
        })
    return videos


def main():
    request = urllib.request.Request(FEED_URL, headers={'User-Agent': 'flutter-weekly'})
    with urllib.request.urlopen(request, timeout=30) as response:
        fresh = parse_feed(response.read().decode('utf-8'))

    existing = {}
    if DATA_FILE.exists():
        existing = {v['id']: v for v in json.loads(DATA_FILE.read_text('utf-8'))['videos']}

    added = sum(1 for v in fresh if v['id'] not in existing)
    for video in fresh:
        existing[video['id']] = video

    videos = sorted(existing.values(), key=lambda v: v['published'], reverse=True)
    payload = {
        'channel': {'name': 'Flutter', 'url': 'https://www.youtube.com/@flutterdev'},
        'updatedAt': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'videos': videos,
    }
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', 'utf-8')
    print(f'{len(fresh)} in feed, {added} new, {len(videos)} total')


if __name__ == '__main__':
    main()
