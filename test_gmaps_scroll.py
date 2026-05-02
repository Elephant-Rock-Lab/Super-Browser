"""Test Google Maps restaurant scraping using SUPER-BROWSER with real CDP mouse wheel events."""

import asyncio
import json
import re
import sys

sys.path.insert(0, "src")

from super_browser.browser.config import SessionConfig
from super_browser.browser.session import BrowserSession
from super_browser.interaction.controller import MultimodalController


async def main():
    # Start a browser session directly (headless=False to see it)
    session = BrowserSession(SessionConfig(headless=False))
    await session.start()
    page = await session.new_page()
    controller = MultimodalController(page, page.cdp)
    cdp = page.cdp
    
    try:
        print("[OK] Browser started")
        
        # Step 1: Navigate to Google Maps search
        print("\n--- Step 1: Navigate to Google Maps ---")
        await page.raw_page.goto(
            "https://www.google.com/maps/search/italian+restaurants+in+Jeddah",
            wait_until="domcontentloaded",
        )
        await asyncio.sleep(5)  # let it fully load
        print(f"[OK] Navigated. URL: {page.url}")
        
        # Step 2: Enable "Update results when map moves" checkbox
        print("\n--- Step 2: Enable checkbox ---")
        snap = await controller.capture_ax_snapshot()
        for node in snap.nodes.values():
            if node.role == "checkbox" and "Update results" in (node.name or ""):
                if node.center:
                    print(f"  Found checkbox at {node.center}, clicking...")
                    await cdp.compositor_click(*node.center)
                    await asyncio.sleep(0.5)
                break
        
        # Step 3: Find the feed element's position
        print("\n--- Step 3: Find feed element ---")
        result = await cdp.evaluate("""
            (function() {
                var feed = document.querySelector('[role="feed"]');
                if (!feed) return JSON.stringify({error: "no feed found"});
                var rect = feed.getBoundingClientRect();
                return JSON.stringify({
                    x: rect.x,
                    y: rect.y,
                    width: rect.width,
                    height: rect.height,
                    scrollHeight: feed.scrollHeight,
                    clientHeight: feed.clientHeight,
                    childCount: feed.children.length
                });
            })()
        """)
        
        feed_info_raw = result.data.get("result", {}).get("value", "{}")
        feed_info = json.loads(feed_info_raw) if isinstance(feed_info_raw, str) else {}
        print(f"  Feed info: {feed_info}")
        
        if "error" in feed_info:
            print(f"[ERROR] {feed_info['error']}")
            return
        
        feed_x = feed_info["x"] + feed_info["width"] / 2
        feed_y = feed_info["y"] + feed_info["height"] / 2
        print(f"  Wheel target: ({feed_x:.0f}, {feed_y:.0f})")
        
        # Step 4: Scroll the feed using real CDP mouse wheel events
        print("\n--- Step 4: Scroll feed with CDP mouse wheel ---")
        
        all_restaurants = set()
        prev_child_count = 0
        no_growth_count = 0
        scroll_round = 0
        
        while no_growth_count < 5:
            scroll_round += 1
            
            # Send wheel events to scroll down
            for _ in range(8):
                await cdp.send("Input.dispatchMouseEvent", {
                    "type": "mouseWheel",
                    "x": feed_x,
                    "y": feed_y,
                    "deltaX": 0,
                    "deltaY": 200,
                })
                await asyncio.sleep(0.15)
            
            await asyncio.sleep(2)  # wait for lazy loading
            
            # Check state
            result = await cdp.evaluate("""
                (function() {
                    var feed = document.querySelector('[role="feed"]');
                    if (!feed) return JSON.stringify({error: "no feed"});
                    return JSON.stringify({
                        scrollHeight: feed.scrollHeight,
                        clientHeight: feed.clientHeight,
                        scrollTop: feed.scrollTop,
                        childCount: feed.children.length
                    });
                })()
            """)
            
            state_raw = result.data.get("result", {}).get("value", "{}")
            state = json.loads(state_raw) if isinstance(state_raw, str) else {}
            
            child_count = state.get("childCount", 0)
            scroll_height = state.get("scrollHeight", 0)
            
            # Get feed text
            result2 = await cdp.evaluate("""
                (function() {
                    var feed = document.querySelector('[role="feed"]');
                    return feed ? feed.textContent : "";
                })()
            """)
            
            feed_text = result2.data.get("result", {}).get("value", "")
            
            # Debug: show first 300 chars of text on first round
            if scroll_round == 1:
                sample = feed_text[500:900].encode('ascii', 'replace').decode('ascii')
                print(f"  Feed text sample: {sample}")
            
            # Parse restaurant names from textContent
            # The text has noise from UI labels. Clean it.
            current_names = set()
            
            # Clean up known Arabic UI prefixes that get concatenated
            ui_prefixes = [
                'الطلب على الإنترنت',  # Order online
                'التسليم بدون تلامس',  # No-contact delivery  
                'خدمة التوصيل',         # Delivery service
                'لا تتوفر خدمة التوصيل', # No delivery
                'الجلوس داخل المكان',   # Dine-in
                'الخدمات في الموقع',     # On-site services
            ]
            # Also clean time prefixes like "يفتح عند الساعة ٤ م"
            clean_text = feed_text
            for prefix in ui_prefixes:
                clean_text = clean_text.replace(prefix, '\n')
            # Clean time lines like "يفتح عند الساعة X"
            clean_text = re.sub(r'يفتح عند الساعة[^\n]*', '', clean_text)
            
            # Method 1: name directly followed by rating pattern
            for m in re.finditer(
                r'([^\n\d]{3,60}?)\s+(\d+\.\d+)\(\d[\d,]*\)',
                clean_text
            ):
                name = m.group(1).strip()
                # Skip UI labels
                skip = {'Results', 'Rating', 'Hours', 'Share', 'Order online',
                        'All filters', 'Menu', 'Saved', 'Recents', 'Get app',
                        'Learn more', 'Update results'}
                if name not in skip and not name.startswith('"') and len(name) > 2:
                    current_names.add(name)
            
            # Method 2: newline-separated name + rating
            lines = clean_text.split('\n')
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped or len(stripped) < 3:
                    continue
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if re.match(r'^[\d]\.\d\(', next_line):
                        skip = {'Results', 'Rating', 'Hours', 'Share', 'Order online'}
                        if stripped not in skip and not stripped.startswith('"'):
                            current_names.add(stripped)
            
            new_names = current_names - all_restaurants
            all_restaurants.update(current_names)
            
            print(f"\n  Round {scroll_round}: children={child_count}, "
                  f"scrollH={scroll_height}, found={len(current_names)}, "
                  f"NEW={len(new_names)}, total={len(all_restaurants)}")
            
            if new_names:
                for name in sorted(new_names):
                    print(f"    + {name}")
                no_growth_count = 0
            else:
                no_growth_count += 1
                print(f"    (no growth, {no_growth_count}/5)")
            
            if child_count == prev_child_count:
                pass  # count toward stagnation via no_growth
            prev_child_count = child_count
            
            if scroll_round > 40:
                print("  [MAX ROUNDS]")
                break
        
        # Step 5: Check for end-of-list
        print("\n--- Step 5: Check end of list ---")
        result = await cdp.evaluate("""
            (function() {
                var body = document.body.innerText || "";
                var feed = document.querySelector('[role="feed"]');
                var feedText = feed ? feed.textContent : "";
                return JSON.stringify({
                    backToTop: body.includes('Back to top') || feedText.includes('Back to top'),
                    endOfList: body.includes('end of the list'),
                    feedLen: feedText.length
                });
            })()
        """)
        end_raw = result.data.get("result", {}).get("value", "{}")
        end_info = json.loads(end_raw) if isinstance(end_raw, str) else {}
        print(f"  Back to top: {end_info.get('backToTop')}")
        print(f"  End of list: {end_info.get('endOfList')}")
        
        # Step 6: Summary
        print(f"\n{'='*60}")
        print(f"TOTAL RESTAURANTS: {len(all_restaurants)}")
        print(f"{'='*60}")
        for i, name in enumerate(sorted(all_restaurants), 1):
            print(f"  {i:2d}. {name}")
        
    finally:
        await session.stop()
        print("\n[OK] Session stopped")


if __name__ == "__main__":
    asyncio.run(main())
