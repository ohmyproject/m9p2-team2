import time

from crawler.utils import clean_text


CLICK_REVIEW_TAB_JS = """
const els = [...document.querySelectorAll('button,a,[role="tab"]')];
const tab = els.find(el => (el.innerText || '').includes('리뷰'));
if (!tab) return false;
tab.scrollIntoView({block: 'center'});
tab.click();
return true;
"""


REVIEW_READY_JS = """
const host = document.querySelector('oy-review-review-in-product');
return !!(host && host.shadowRoot);
"""


REVIEW_COUNT_JS = """
const host = document.querySelector('oy-review-review-in-product');
const root = host?.shadowRoot;
if (!root) return '';

const text = root.innerText || '';
const match = text.match(/[0-9,]+/);

return match ? match[0] : '';
"""


EXTRACT_REVIEWS_JS = """
const s1 = document.querySelector('oy-review-review-in-product')?.shadowRoot;
const s2 = s1?.querySelector('oy-review-review-list')?.shadowRoot;
if (!s2) return [];

const items = s2.querySelectorAll('oy-review-review-item');
const results = [];

items.forEach((item) => {
    try {
        const root = item.shadowRoot;
        if (!root) return;

        let stars = 0;
        root.querySelectorAll('oy-review-star-icon').forEach(icon => {
            const path = icon.shadowRoot?.querySelector('path');
            if (path?.getAttribute('fill') === '#FF5753') stars++;
        });

        const userRoot = root.querySelector('oy-review-review-user')?.shadowRoot;
        const skin = [...(userRoot?.querySelectorAll('.skin-type') || [])]
            .map(el => el.innerText.trim())
            .filter(Boolean)
            .join('/');

        const contentRoot = root.querySelector('oy-review-review-content')?.shadowRoot;
        const content = contentRoot?.querySelector('p')?.innerText?.trim() || '';

        if (content) {
            results.push({
                stars: stars,
                skin: skin,
                content: content
            });
        }
    } catch(e) {}
});

return results;
"""


CLICK_NEXT_REVIEW_PAGE_JS = """
const s1 = document.querySelector('oy-review-review-in-product')?.shadowRoot;
const s2 = s1?.querySelector('oy-review-review-list')?.shadowRoot;
if (!s2) return false;

const candidates = [...s2.querySelectorAll('button,a')];

const nextBtn = candidates.find(el => {
    const text = (el.innerText || '').trim();
    const aria = (el.getAttribute('aria-label') || '').trim();
    const title = (el.getAttribute('title') || '').trim();
    const cls = (el.className || '').toString();

    return (
        text.includes('다음') ||
        aria.includes('다음') ||
        title.includes('다음') ||
        aria.toLowerCase().includes('next') ||
        title.toLowerCase().includes('next') ||
        cls.toLowerCase().includes('next')
    );
});

if (!nextBtn) return false;

const disabled =
    nextBtn.disabled ||
    nextBtn.getAttribute('aria-disabled') === 'true' ||
    nextBtn.className.toString().includes('disabled');

if (disabled) return false;

nextBtn.scrollIntoView({block: 'center'});
nextBtn.click();

return true;
"""


def collect_reviews(driver, product_row, limit=10):
    if limit <= 0:
        return []

    rows = []

    sort_type = product_row.get("sort_type", "")
    rank = product_row.get("rank", "")
    product_name = product_row.get("product_name", "")
    review_count = product_row.get("review_count", 0)
    product_url = product_row.get("url", "")
    main_ingredients = product_row.get("main_ingredients", "")
    date = product_row.get("date", "")
    platform = product_row.get("platform", "oliveyoung")

    if not driver.execute_script(CLICK_REVIEW_TAB_JS):
        print("  [리뷰] 리뷰 탭 클릭 실패")
        return rows

    time.sleep(1.5)

    for _ in range(10):
        if driver.execute_script(REVIEW_READY_JS):
            break

        driver.execute_script("window.scrollBy(0, 900);")
        time.sleep(1)

    total_review_count = driver.execute_script(REVIEW_COUNT_JS) or review_count

    seen = set()
    max_pages = 5
    page_try = 0
    no_new_count = 0

    while len(rows) < limit and page_try < max_pages:
        raw_reviews = driver.execute_script(EXTRACT_REVIEWS_JS) or []
        before_count = len(rows)

        print(f"  [리뷰] page_try={page_try + 1}, 화면 리뷰 후보 {len(raw_reviews)}개")

        for raw in raw_reviews:
            review_text = clean_text(raw.get("content", ""))

            if not review_text:
                continue

            if review_text in seen:
                continue

            rows.append(
                {
                    "date": date,
                    "platform": platform,
                    "sort_type": sort_type,
                    "rank": rank,
                    "main_ingredients": main_ingredients,
                    "product_name": product_name,
                    "review_count": total_review_count,
                    "review_rating": raw.get("stars", ""),
                    "skin_type": clean_text(raw.get("skin", "")),
                    "review_text": review_text,
                    "url": product_url,
                }
            )

            seen.add(review_text)

            if len(rows) >= limit:
                break

        if len(rows) >= limit:
            break

        if len(rows) == before_count:
            no_new_count += 1
        else:
            no_new_count = 0

        clicked = driver.execute_script(CLICK_NEXT_REVIEW_PAGE_JS)

        if clicked:
            print("  [리뷰] 다음 리뷰 페이지 클릭")
            time.sleep(1.8)
        else:
            print("  [리뷰] 다음 버튼 없음, 스크롤 추가")
            driver.execute_script("window.scrollBy(0, 1200);")
            time.sleep(1.2)

        if no_new_count >= 3:
            print("  [리뷰] 새 리뷰가 더 이상 늘지 않아 중단")
            break

        page_try += 1

    print(f"  [리뷰] 수집 {len(rows)}건 / 전체 리뷰수 {total_review_count}")
    return rows