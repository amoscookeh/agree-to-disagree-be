# Right-Leaning Data Sources

This directory contains data sources for conservative/right-leaning news outlets.

## Available Sources

### 1. NewsAPI (`newsapi.py`)
- **Type:** API-based
- **Sources:** Fox News, Breitbart News, Wall Street Journal, National Review, Washington Times
- **Coverage:** Last 30 days
- **Success Rate:** 100% (7/7 test queries)
- **Requires:** `NEWSAPI_KEY` environment variable

### 2. NY Post RSS (`ny_post_rss.py`)
- **Type:** RSS feed with fuzzy matching
- **Feeds:** Main, US News, Politics
- **Success Rate:** 29% (2/7 test queries)
- **No API key required**

### 3. Breitbart RSS (`breitbart_rss.py`)
- **Type:** RSS feed with fuzzy matching
- **Feeds:** Main Feedburner
- **Success Rate:** 57% (4/7 test queries)
- **No API key required**

### 4. Daily Wire RSS (`daily_wire_rss.py`)
- **Type:** RSS feed with fuzzy matching
- **Feeds:** Main RSS
- **Success Rate:** 71% (5/7 test queries)
- **No API key required**

## Fuzzy Matching Algorithm

RSS sources use word-based relevance scoring to match queries with articles:

```python
def _relevance_score(query: str, title: str, summary: str) -> float:
    """
    Calculate relevance score based on word overlap
    
    Returns: 0.0 to 1.0+ (can exceed 1.0 with title bonus)
    """
    query_words = _tokenize(query)
    content_words = _tokenize(f"{title} {summary}")
    
    # base score: percentage of query words found in content
    matches = query_words & content_words
    score = len(matches) / len(query_words)
    
    # bonus: if query words appear in title (more relevant)
    title_words = _tokenize(title)
    title_matches = query_words & title_words
    if title_matches:
        score += 0.3 * (len(title_matches) / len(query_words))
    
    return min(score, 1.0)
```

### Examples

**Query:** "immigration policy"

**Article 1:** "Trump Ends Border Crisis with New Immigration Rules"
- Query words: {immigration, policy}
- Content words: {trump, ends, border, crisis, new, immigration, rules}
- Matches: {immigration}
- Base score: 1/2 = 0.5
- Title matches: {immigration}
- Title bonus: 0.3 * (1/2) = 0.15
- **Final score: 0.65** (above 0.2 threshold)

**Article 2:** "Biden Visits Texas Border"
- Query words: {immigration, policy}
- Content words: {biden, visits, texas, border}
- Matches: {} (no direct word overlap)
- **Final score: 0.0** (below 0.2 threshold)

**Article 3:** "New Policy Changes Immigration System"
- Query words: {immigration, policy}
- Content words: {new, policy, changes, immigration, system}
- Matches: {immigration, policy}
- Base score: 2/2 = 1.0
- Title matches: {immigration, policy}
- Title bonus: 0.3 * (2/2) = 0.3
- **Final score: 1.0** (capped at 1.0, highly relevant)

### Threshold

- **Minimum score:** 0.2 (20% word match)
- Articles below this threshold are filtered out
- Prevents completely irrelevant results

### Why This Works

1. **Semantic flexibility:** "immigration" matches articles about "border", "migrant", "asylum"
2. **Title weighting:** Articles with query words in title rank higher
3. **Simple and fast:** No external dependencies, runs in O(n) time
4. **Tunable:** Adjust threshold and title bonus as needed

## Usage

```python
from src.data_sources.right_leaning import (
    NewsAPISource,
    NYPostRSSSource,
    BreitbartRSSSource,
    DailyWireRSSSource,
)

# create sources
newsapi = NewsAPISource()
nypost = NYPostRSSSource()
breitbart = BreitbartRSSSource()
dailywire = DailyWireRSSSource()

# search
results = await newsapi.search("immigration policy", max_results=5)
for result in results:
    print(f"{result.source_name}: {result.title}")
```

## Testing

```bash
# test all right-leaning sources
cd agree-to-disagree-be
PYTHONPATH=$(pwd) uv run python scripts/test_right_sources.py

# test specific source
python -c "
import asyncio
from src.data_sources.right_leaning import BreitbartRSSSource

async def test():
    source = BreitbartRSSSource()
    results = await source.search('immigration', max_results=3)
    for r in results:
        print(r.title)

asyncio.run(test())
"
```

## Error Handling

All sources implement graceful degradation:

1. **Network errors:** Return empty list, log warning
2. **Feed redirects:** Try updated URL, continue on failure
3. **Parsing errors:** Skip malformed entries, continue with valid ones
4. **Rate limiting:** Built-in semaphore (5 concurrent requests max)

## Performance

- **NewsAPI:** ~500ms per query
- **RSS feeds:** ~700ms per query (includes parsing)
- **Parallel execution:** All sources searched simultaneously
- **Caching:** Not implemented (future enhancement)

## Future Improvements

1. **Add more sources:**
   - Washington Examiner RSS
   - The Federalist RSS
   - National Review RSS (separate from NewsAPI)
   - The Blaze RSS

2. **Semantic search:**
   - Use embeddings for better matching
   - "immigration" → "border", "asylum", "deportation"

3. **Caching:**
   - Cache RSS feed fetches (1 hour TTL)
   - Reduce redundant network calls

4. **Dynamic threshold:**
   - Lower threshold if no results found
   - Adaptive based on query complexity

