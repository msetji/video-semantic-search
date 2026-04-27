# Error Analysis: CLIP-Based Semantic Search Failure Cases

This document analyzes some of the failure modes of our CLIP-based semantic video and photo search system that have presented themselves during testing. We ran a set of queries, ranging from concrete to abstract and compositional, and identified one main category where the model struggles. 

---
## Background: How CLIP Retrieves Results

Our system encodes the search query into a 512-dimensional text embedding using CLIP's text encoder (`openai/clip-vit-large-patch14`). At index time, each video frame is encoded into the same 512-dimensional space using CLIP's vision encoder. Search is performed via FAISS `IndexFlatIP` (inner product / cosine similarity) over L2-normalized vectors.
---

## Failure Categories

### 1. Abstract Concepts

**Queries tested:** `"love"`, `"anger"`

**Expected behavior:** Return images that evoke the specified concept, such as an hugging or laughter for "love."

**Observed behavior:** Results are inconsistent and presents almost random clips such as walking or a road. CLIP's text embedding for an abstract word like "love" does not align with images that a human would associate with that feeling. 

**Why CLIP fails here:** CLIP learns associations between visual patterns and the words that describe them literally. Abstract concepts rarely appear as image captions on the web for the open-source model used. The word "love" might appear in captions like "love is hard" (an image containing that text somewhere in it), so its embedding is not anchored to any coherent visual feature.

**Screenshot:** `screenshots/error_love_query.png`


## Discussion and Potential Mitigations

These failure modes are fundamental to CLIP's architecture rather than implementation bugs. Potential improvements include:

- **Query expansion:** Rewrite abstract queries into concrete visual descriptions before embedding (e.g. using a language model to expand "love" → "physical contact, laughter").

Understanding these failure modes is critical for setting user expectations about what kinds of queries the system can and cannot handle reliably.