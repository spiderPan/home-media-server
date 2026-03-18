# -*- coding: utf-8 -*-
from __future__ import absolute_import
import base64
import io
import logging
import os
import zipfile
import re
import copy
from PIL import Image

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

import rarfile
import pytesseract
from babelfish import language_converters
from subzero.language import Language
from guessit import guessit
from requests import Session
from six import text_type
from random import randint, randrange

from subliminal.providers import ParserBeautifulSoup
from subliminal_patch.providers import Provider
from subliminal.subtitle import (
    SUBTITLE_EXTENSIONS,
    fix_line_ending
)
from subliminal_patch.subtitle import (
    Subtitle,
    guess_matches
)
from .utils import FIRST_THOUSAND_OR_SO_USER_AGENTS as AGENT_LIST
from subliminal.video import Episode, Movie

logger = logging.getLogger(__name__)

class YifySubtitlesSubtitle(Subtitle):
    """YifySubtitles Subtitle (Actually SubHD)."""
    provider_name = "yifysubtitles"

    def __init__(self, language, page_link, version, session, year):
        super(YifySubtitlesSubtitle, self).__init__(language, page_link=page_link)
        self.version = version
        self.release_info = version
        self.hearing_impaired = False
        self.encoding = "utf-8"
        self.session = session
        self.year = year
        self.matches = set()

    @property
    def id(self):
        return self.page_link

    def get_matches(self, video):
        if video.year == self.year:
            self.matches.add('year')

        # episode
        if isinstance(video, Episode):
            info = guessit(self.version, {"type": "episode"})
            # other properties
            self.matches |= guess_matches(video, info)

            # add year to matches if video doesn't have a year but series, season and episode are matched
            if not video.year and all(item in self.matches for item in ['series', 'season', 'episode']):
                self.matches |= {'year'}
        # movie
        elif isinstance(video, Movie):
            # other properties
            self.matches |= guess_matches(video, guessit(self.version, {"type": "movie"}))

        return self.matches


def string_to_hex(s):
    val = ""
    for i in s:
        val += hex(ord(i))[2:]
    return val


class YifySubtitlesProvider(Provider):
    """YifySubtitles Provider (Actually SubHD with Login)."""

    languages = {Language('zho'), Language('eng')}
    video_types = (Episode, Movie)

    server_url = "https://subhd.tv"
    search_url = "/search/{}"

    subtitle_class = YifySubtitlesSubtitle

    def __init__(self):
        self.session = None
        self.email = "panbanglanfeng@gmail.com"
        self.password = "subhd2026"

    verify_token = ""
    code = ""
    location_re = re.compile(
        r'self\.location = "(.*)" \+ stringToHex\(')
    verification_image_re = re.compile(r'<img.*?src="data:image/bmp;base64,(.*?)".*?>')

    def yunsuo_bypass(self, url, *args, **kwargs):
        def parse_verification_image(image_content: str):
            try:
                # The regex stripped the prefix, decode the base64
                image_bytes = base64.b64decode(image_content)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Tell Tesseract to ONLY look for numbers, and treat it as a single word (psm 8)
                custom_config = r'--psm 8 -c tessedit_char_whitelist=0123456789'
                captcha_text = pytesseract.image_to_string(image, config=custom_config).strip()
                
                logger.info(f"[SubHD OCR] Successfully solved CAPTCHA: {captcha_text}")
                return captcha_text
            except Exception as e:
                logger.error(f"[SubHD OCR] OCR Failed: {e}")
                return ""
            
        i = -1
        while True:
            i += 1
            if i > 10:
                break
            r = self.session.get(url, *args, **kwargs)
            if r.status_code == 404:
                # mock js script logic
                tr = self.location_re.findall(r.text)
                verification_image = self.verification_image_re.findall(r.text)
                if len(verification_image):
                    self.code = parse_verification_image(verification_image[0])
                else:
                    self.code = f"{randrange(800, 1920)},{randrange(600, 1080)}"
                self.session.cookies.set("srcurl", string_to_hex(r.url))
                if tr:
                    verify_resp = self.session.get(
                        urljoin(self.server_url, tr[0] + string_to_hex(self.code)), allow_redirects=False)
                    if verify_resp.status_code == 302 \
                            and self.session.cookies.get("security_session_verify") is not None:
                        pass
                    continue
            if len(self.location_re.findall(r.text)) == 0:
                self.verify_token = string_to_hex(self.code)
                return r
        return r

    def initialize(self):
        self.session = Session()
        self.session.headers["User-Agent"] = AGENT_LIST[randint(0, len(AGENT_LIST) - 1)]
        
        # Perform Login
        logger.info("[SubHD] Attempting login for %s", self.email)
        login_url = urljoin(self.server_url, "/api/set/login")
        payload = {
            "email": self.email,
            "pwd": self.password
        }
        headers = {
            "Content-Type": "application/json",
            "Referer": urljoin(self.server_url, "/set/login"),
            "X-Requested-With": "XMLHttpRequest"
        }
        
        try:
            # Need to visit login page first maybe for cookies?
            self.yunsuo_bypass(urljoin(self.server_url, "/set/login"))
            
            r = self.session.post(login_url, json=payload, headers=headers, timeout=30)
            if r.status_code == 200:
                data = r.json()
                if data.get("success"):
                    logger.info("[SubHD] Login successful!")
                else:
                    logger.error("[SubHD] Login failed: %s", data.get("msg"))
            else:
                logger.error("[SubHD] Login failed with status: %s", r.status_code)
        except Exception as e:
            logger.error("[SubHD] Login exception: %s", e)

    def terminate(self):
        self.session.close()

    def _parse_search_results(self, html, year):
        soup = ParserBeautifulSoup(html, ["lxml", "html.parser"])
        subtitles = []
        
        # SubHD search results are often in <a> tags with href starting with /a/
        items = soup.find_all('a', href=re.compile(r'^/a/'))
        logger.info("[SubHD] Found %d potential links on page", len(items))
        
        for a in items:
            name = a.get_text(strip=True)
            if not name or len(name) < 5: # Skip very short names (like icons or small labels)
                continue
                
            page_link = urljoin(self.server_url, a.attrs["href"])
            logger.info("[SubHD] Found result: %s -> %s", name, page_link)
            
            language = Language("zho")
            if any(x in name.lower() for x in ["繁体", "cht", "tc"]):
                language = Language('zho', 'TW', None)

            subtitles.append(
                self.subtitle_class(language, page_link, name, self.session, year)
            )
            
        return subtitles

    def query(self, keyword, season=None, episode=None, year=None):
        params = keyword
        if season:
            params += " S{:02d}".format(season)
        elif year:
            params += " {:4d}".format(year)

        logger.info("[SubHD] Searching for: %r", params)
        search_link = urljoin(self.server_url, text_type(self.search_url).format(params))

        r = self.yunsuo_bypass(search_link, timeout=30)
        r.raise_for_status()

        if not r.content:
            return []

        return self._parse_search_results(r.content.decode("utf-8", "ignore"), year)

    def list_subtitles(self, video, languages):
        logger.info("[SubHD] list_subtitles called for video: %r", video)
        if isinstance(video, Episode):
            titles = [video.series] + video.alternative_series
        elif isinstance(video, Movie):
            titles = [video.title] + video.alternative_titles
        else:
            titles = []

        subtitles = []
        for title in titles:
            query_args = {'keyword': title, 'year': video.year}
            if isinstance(video, Episode):
                query_args['season'] = video.season
                query_args['episode'] = video.episode
            
            results = self.query(**query_args)
            for s in results:
                if s.language in languages:
                    subtitles.append(s)

        logger.info("[SubHD] Total matching subtitles found: %d", len(subtitles))
        return subtitles

    def download_subtitle(self, subtitle):
        logger.info("[SubHD] Downloading subtitle: %r", subtitle.page_link)
        
        # 1. Get the detail page to find the /down/ link
        r = self.yunsuo_bypass(subtitle.page_link)
        r.raise_for_status()
        soup = ParserBeautifulSoup(r.content.decode("utf-8", "ignore"), ["html.parser"])
        
        down_a = soup.find('a', href=re.compile(r'^/down/'))
        if not down_a:
            logger.error("[SubHD] Could not find /down/ link on page")
            return

        down_page_link = urljoin(self.server_url, down_a.attrs["href"])
        logger.info("[SubHD] Navigating to download page: %s", down_page_link)

        # 2. Get the /down/ page to get cookies and sid
        r = self.yunsuo_bypass(down_page_link, headers={'Referer': subtitle.page_link})
        r.raise_for_status()
        
        if "验证" in r.text and "验证中" not in r.text:
             # If still blocked after login, we have a problem
             logger.warning("[SubHD] Page still shows 'Verification' after login. Trying to proceed anyway...")

        soup = ParserBeautifulSoup(r.content.decode("utf-8", "ignore"), ["html.parser"])
        sid = None
        down_btn = soup.find(attrs={"sid": True})
        if down_btn:
            sid = down_btn.get('sid')
        
        if not sid:
            match = re.search(r'sid=\"([^\"]+)\"', r.text)
            if match:
                sid = match.group(1)

        if not sid:
            logger.error("[SubHD] Could not find sid on download page")
            return
        
        logger.info("[SubHD] Found sid: %s", sid)

        # 3. POST to /ajax/down_ajax to get the real download link
        ajax_url = urljoin(self.server_url, "/ajax/down_ajax")
        headers = {
            'Referer': down_page_link,
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': self.server_url
        }
        data = {'sub_id': sid}
        
        resp = self.session.post(ajax_url, data=data, headers=headers, timeout=30)
        logger.info("[SubHD] AJAX response status: %s", resp.status_code)
        
        try:
            ajax_data = resp.json()
            download_link = ajax_data.get('url')
        except Exception as e:
            logger.error("[SubHD] Failed to parse AJAX JSON: %s (Response: %r)", e, resp.text)
            return

        if not download_link:
            logger.error("[SubHD] No download link in AJAX response: %r", resp.text)
            return

        logger.info("[SubHD] Direct download link: %s", download_link)

        # 4. Download the actual file
        r = self.yunsuo_bypass(download_link, headers={'Referer': down_page_link}, timeout=30)
        r.raise_for_status()
        
        if not r.content:
            logger.error("[SubHD] Downloaded content is empty")
            return

        filename = r.headers.get("Content-Disposition", "").lower()
        logger.info("[SubHD] Downloaded file name: %s, size: %d bytes", filename, len(r.content))
        archive_stream = io.BytesIO(r.content)
        
        subtitle_content = None
        if rarfile.is_rarfile(archive_stream):
            archive = rarfile.RarFile(archive_stream)
            subtitle_content = _get_subtitle_from_archive(archive)
        elif zipfile.is_zipfile(archive_stream):
            archive = zipfile.ZipFile(archive_stream)
            subtitle_content = _get_subtitle_from_archive(archive)
        else:
            is_sub = False
            for sub_ext in SUBTITLE_EXTENSIONS:
                if sub_ext in filename or r.url.lower().endswith(sub_ext):
                    is_sub = True
                    break
            if is_sub:
                subtitle_content = r.content
            else:
                logger.debug("Unknown file type: %s", filename)

        if subtitle_content:
            subtitle.content = fix_line_ending(subtitle_content)
            logger.info("[SubHD] Successfully extracted subtitle")
        else:
            logger.error("[SubHD] Could not extract subtitle from download")


def _get_subtitle_from_archive(archive):
    extract_subname, max_score = "", -1

    for subname in archive.namelist():
        if os.path.split(subname)[-1].startswith("."):
            continue
        if not subname.lower().endswith(SUBTITLE_EXTENSIONS):
            continue

        score = ("ass" in subname or "ssa" in subname or "srt" in subname) * 1
        if any(x in subname for x in ["简体", "chs", ".gb."]):
            score += 2
        if any(x in subname for x in ["繁体", "cht", ".big5."]):
            score += 2
        if any(x in subname for x in ["chs.eng", "chs&eng", "cht.eng", "cht&eng"]):
            score += 2
        if any(x in subname for x in ["中英", "简英", "繁英", "双语", "简体&英文", "繁体&英文"]):
            score += 4
            
        if score > max_score:
            max_score = score
            extract_subname = subname

    return archive.read(extract_subname) if max_score != -1 else None
