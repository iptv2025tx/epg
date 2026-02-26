#!/usr/bin/env python3
"""
EPG Combiner Script
Fetches EPG XML files from multiple sources and combines them into one.
Run daily via cron or GitHub Actions to keep EPG data fresh.

Usage:
    python combine_epg.py
    python combine_epg.py --output combined_epg.xml

Requirements:
    pip install certifi
"""

import argparse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import ssl
import gzip
import os

# Try to import certifi for SSL certificates
try:
    import certifi
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    # Fall back to default SSL context (works on GitHub Actions)
    SSL_CONTEXT = ssl.create_default_context()

from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# EPG Sources from globetvapp/epg repository
EPG_SOURCES = {
    # United States
    "usa1": "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml",
    "usa2": "https://github.com/matthuisman/i.mjh.nz/raw/master/SamsungTVPlus/us.xml",
    "usa3": "https://github.com/matthuisman/i.mjh.nz/raw/master/PlutoTV/us.xml",
    "usa4": "https://github.com/matthuisman/i.mjh.nz/raw/master/Plex/us.xml",
    "usa5": "",

    # United Kingdom
    "uk1": "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom1.xml",
    "uk2": "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom2.xml",
    "uk3": "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom3.xml",
    "uk4": "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom4.xml",
    "uk5": "https://raw.githubusercontent.com/globetvapp/epg/main/Unitedkingdom/unitedkingdom5.xml",

    # Sports (International)
    "sports1": "https://raw.githubusercontent.com/globetvapp/epg/main/Sports/sports1.xml",
    "sports2": "https://raw.githubusercontent.com/globetvapp/epg/main/Sports/sports2.xml",
    "sports3": "https://raw.githubusercontent.com/globetvapp/epg/main/Sports/sports3.xml",

    # Canada
    "canada1": "https://raw.githubusercontent.com/globetvapp/epg/main/Canada/canada1.xml",
    "canada2": "https://raw.githubusercontent.com/globetvapp/epg/main/Canada/canada2.xml",

    # Ireland
    "ireland1": "https://raw.githubusercontent.com/globetvapp/epg/main/Ireland/ireland1.xml",

    # Australia
    "australia1": "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia1.xml",
    "australia2": "https://raw.githubusercontent.com/globetvapp/epg/main/Australia/australia2.xml",
}

def fetch_epg(name, url):
    """Fetch and parse an EPG XML file."""
    try:
        print(f"  Fetching {name}...", end=" ", flush=True)

        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept-Encoding": "gzip, deflate"
        })

        with urlopen(req, timeout=60, context=SSL_CONTEXT) as response:
            data = response.read()

            # Handle gzip compression
            if url.endswith('.gz') or response.headers.get('Content-Encoding') == 'gzip':
                data = gzip.decompress(data)

            # Parse XML
            root = ET.fromstring(data)

            channels = len(root.findall('channel'))
            programmes = len(root.findall('programme'))
            print(f"OK ({channels} channels, {programmes} programmes)")

            return name, root, None

    except (URLError, HTTPError) as e:
        print(f"FAILED ({e})")
        return name, None, str(e)
    except ET.ParseError as e:
        print(f"PARSE ERROR ({e})")
        return name, None, str(e)
    except Exception as e:
        print(f"ERROR ({e})")
        return name, None, str(e)

def combine_epg_files(sources, max_workers=5):
    """Fetch and combine multiple EPG sources into one XML tree."""

    # Create root element
    combined = ET.Element('tv')
    combined.set('generator-info-name', 'CouchStreaming EPG Combiner')
    combined.set('generator-info-url', 'https://github.com/globetvapp/epg')
    combined.set('date', datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S'))

    # Track unique channels to avoid duplicates
    seen_channels = set()
    seen_programmes = set()

    total_channels = 0
    total_programmes = 0
    failed_sources = []

    print(f"\nFetching {len(sources)} EPG sources...")

    # Fetch all sources in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(fetch_epg, name, url): name
            for name, url in sources.items()
        }

        for future in as_completed(futures):
            name, root, error = future.result()

            if error:
                failed_sources.append((name, error))
                continue

            if root is None:
                continue

            # Add channels (avoiding duplicates)
            for channel in root.findall('channel'):
                channel_id = channel.get('id', '')
                if channel_id and channel_id not in seen_channels:
                    seen_channels.add(channel_id)
                    combined.append(channel)
                    total_channels += 1

            # Add programmes (avoiding exact duplicates)
            for programme in root.findall('programme'):
                # Create a unique key for the programme
                prog_key = (
                    programme.get('channel', ''),
                    programme.get('start', ''),
                    programme.get('stop', '')
                )

                if prog_key not in seen_programmes:
                    seen_programmes.add(prog_key)
                    combined.append(programme)
                    total_programmes += 1

    print(f"\n{'='*50}")
    print(f"Combined EPG Statistics:")
    print(f"  Total channels: {total_channels}")
    print(f"  Total programmes: {total_programmes}")
    print(f"  Sources succeeded: {len(sources) - len(failed_sources)}/{len(sources)}")

    if failed_sources:
        print(f"\nFailed sources:")
        for name, error in failed_sources:
            print(f"  - {name}: {error}")

    return combined

def write_xml(root, output_path):
    """Write the XML tree to a file with proper formatting."""

    # Convert to string
    xml_str = ET.tostring(root, encoding='unicode')

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(xml_str)

    print(f"\nOutput written to: {output_path}")

    # Get file size
    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"File size: {size_mb:.2f} MB")

def main():
    parser = argparse.ArgumentParser(description='Combine multiple EPG XML sources into one file')
    parser.add_argument('--output', '-o', default='epg.xml', help='Output file path')
    parser.add_argument('--workers', '-w', type=int, default=5, help='Number of parallel downloads')
    parser.add_argument('--list', '-l', action='store_true', help='List available sources')
    args = parser.parse_args()

    if args.list:
        print("Available EPG sources:")
        for name, url in sorted(EPG_SOURCES.items()):
            print(f"  {name}: {url}")
        return

    print("EPG Combiner - CouchStreaming")
    print("="*50)

    # Combine all sources
    combined = combine_epg_files(EPG_SOURCES, max_workers=args.workers)

    # Write output
    write_xml(combined, args.output)

    print("\nDone! You can now use this combined EPG file in your app.")
    print(f"URL (if hosted): https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/{args.output}")

if __name__ == '__main__':
    main()
