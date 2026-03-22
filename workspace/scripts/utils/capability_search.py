def get_related_capabilities(event: dict, capabilities: list, max_n: int = 3) -> list:
    """
    三级降级检索：精确匹配 → 本地 TF-IDF → 空列表
    任何情况下都不调用 LLM 或 Embedding API
    """
    # 级别 1：精确匹配 capability_ids
    if event.get("capability_ids"):
        exact = [
            cap for cap in capabilities
            if cap["capability_id"] in event["capability_ids"]
        ]
        if exact:
            return exact[:max_n]

    # 级别 2：本地 TF-IDF
    query = " ".join(filter(None, [
        event.get("title", ""),
        event.get("content", ""),
        event.get("task_type", "")
    ]))
    corpus = [
        " ".join(filter(None, [
            cap.get("display_name", ""),
            cap.get("category", ""),
            " ".join(cap.get("aliases", []))
        ]))
        for cap in capabilities
    ]

    if corpus and query.strip():
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(corpus + [query])
            scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
            top_idx = np.argsort(scores)[::-1][:max_n]
            matched = [capabilities[i] for i in top_idx if scores[i] > 0.1]
            if matched:
                return matched
        except Exception:
            pass

    # 级别 3：返回空列表
    return []


def get_related_antipatterns(event: dict, antipatterns: list, max_n: int = 3) -> list:
    """
    同样的三级降级逻辑，用于检索相关 antipattern
    """
    if event.get("antipattern_ids"):
        exact = [
            ap for ap in antipatterns
            if ap["antipattern_id"] in event["antipattern_ids"]
        ]
        if exact:
            return exact[:max_n]

    query = " ".join(filter(None, [
        event.get("title", ""),
        event.get("content", ""),
        event.get("task_type", "")
    ]))
    corpus = [
        " ".join(filter(None, [
            ap.get("scene", ""),
            ap.get("trap", ""),
            ap.get("correct_action", "")
        ]))
        for ap in antipatterns
    ]

    if corpus and query.strip():
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np

            vectorizer = TfidfVectorizer()
            matrix = vectorizer.fit_transform(corpus + [query])
            scores = cosine_similarity(matrix[-1], matrix[:-1])[0]
            top_idx = np.argsort(scores)[::-1][:max_n]
            matched = [antipatterns[i] for i in top_idx if scores[i] > 0.1]
            if matched:
                return matched
        except Exception:
            pass

    return []
