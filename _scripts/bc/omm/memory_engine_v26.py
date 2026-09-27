#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenMemo v26.0 Alpha 8 - 高级记忆管理引擎
GitHub@StarsailsClover

前沿技术集成:
- 向量语义搜索(TF-IDF + 余弦相似度)
- 艾宾浩斯遗忘曲线模拟
- 记忆巩固机制(睡眠式整合)
- 知识图谱实体关系提取
- 记忆激活传播算法
- 多标签智能分类
- 记忆权重衰减系统
- 上下文窗口动态管理
- 记忆重要性自适应评估
"""

import os
import re
import json
import math
import time
import random
import hashlib
import threading
from collections import defaultdict, OrderedDict
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Set
from datetime import datetime, timedelta


# ============================================================================
# 工具函数
# ============================================================================

def tokenize(text: str) -> List[str]:
    """简单分词(中英文混合)"""
    # 英文按空格和标点分割
    text = text.lower()
    # 提取英文单词
    english_words = re.findall(r'[a-zA-Z]+', text)
    # 提取中文单字(简单处理,实际可用jieba)
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    # 提取中文双字词
    chinese_bigrams = []
    for i in range(len(chinese_chars) - 1):
        chinese_bigrams.append(chinese_chars[i] + chinese_chars[i + 1])

    return english_words + chinese_chars + chinese_bigrams


def cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """计算余弦相似度"""
    common = set(vec1.keys()) & set(vec2.keys())
    dot_product = sum(vec1[k] * vec2[k] for k in common)

    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))

    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)


# ============================================================================
# 向量搜索引擎
# ============================================================================

class VectorSearchEngine:
    """基于TF-IDF的轻量级向量搜索引擎"""

    def __init__(self):
        self.documents: Dict[str, str] = {}  # page_id -> content
        self.doc_vectors: Dict[str, Dict[str, float]] = {}  # page_id -> tfidf vector
        self.idf: Dict[str, float] = {}  # 逆文档频率
        self.doc_count: int = 0

    def add_document(self, page_id: str, content: str):
        """添加文档"""
        self.documents[page_id] = content
        self.doc_count += 1
        self._recompute_idf()
        self._compute_tfidf(page_id)

    def remove_document(self, page_id: str):
        """移除文档"""
        if page_id in self.documents:
            del self.documents[page_id]
            self.doc_count -= 1
            if page_id in self.doc_vectors:
                del self.doc_vectors[page_id]
            self._recompute_idf()

    def update_document(self, page_id: str, content: str):
        """更新文档"""
        if page_id in self.documents:
            self.documents[page_id] = content
            self._compute_tfidf(page_id)

    def _compute_tf(self, text: str) -> Dict[str, float]:
        """计算词频"""
        tokens = tokenize(text)
        tf = defaultdict(float)
        total = len(tokens)
        if total == 0:
            return tf
        for token in tokens:
            tf[token] += 1.0 / total
        return dict(tf)

    def _recompute_idf(self):
        """重新计算逆文档频率"""
        doc_freq = defaultdict(int)
        for content in self.documents.values():
            tokens = set(tokenize(content))
            for token in tokens:
                doc_freq[token] += 1

        self.idf = {}
        for token, df in doc_freq.items():
            self.idf[token] = math.log((self.doc_count + 1) / (df + 1)) + 1

    def _compute_tfidf(self, page_id: str):
        """计算TF-IDF向量"""
        content = self.documents.get(page_id, "")
        tf = self._compute_tf(content)
        tfidf = {}
        for token, freq in tf.items():
            tfidf[token] = freq * self.idf.get(token, 1.0)
        self.doc_vectors[page_id] = tfidf

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """语义搜索,返回 (page_id, similarity_score) 列表"""
        query_tf = self._compute_tf(query)
        query_vector = {}
        for token, freq in query_tf.items():
            query_vector[token] = freq * self.idf.get(token, 1.0)

        scores = []
        for page_id, doc_vector in self.doc_vectors.items():
            sim = cosine_similarity(query_vector, doc_vector)
            if sim > 0:
                scores.append((page_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_similar(self, page_id: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """查找相似页面"""
        if page_id not in self.doc_vectors:
            return []

        target_vector = self.doc_vectors[page_id]
        scores = []
        for other_id, doc_vector in self.doc_vectors.items():
            if other_id == page_id:
                continue
            sim = cosine_similarity(target_vector, doc_vector)
            if sim > 0:
                scores.append((other_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ============================================================================
# 艾宾浩斯遗忘曲线
# ============================================================================

class ForgettingCurve:
    """艾宾浩斯遗忘曲线模拟器

    R = e^(-t/S)
    R: 记忆保持率
    t: 时间
    S: 记忆强度(由复习次数和间隔决定)
    """

    def __init__(self):
        self.base_strength = 1.0  # 基础记忆强度
        self.review_boost = 1.5   # 每次复习的强度提升倍数
        self.max_strength = 10.0  # 最大记忆强度

    def calculate_retention(self, last_review: float, strength: float, current_time: float = None) -> float:
        """计算记忆保持率 (0-1)"""
        if current_time is None:
            current_time = time.time()

        time_passed = current_time - last_review  # 秒
        # 转换为小时级别
        hours_passed = time_passed / 3600.0

        # R = e^(-t/S)
        effective_strength = max(strength, 0.1)
        retention = math.exp(-hours_passed / effective_strength)

        return max(0.0, min(1.0, retention))

    def review(self, strength: float) -> float:
        """复习后更新记忆强度"""
        new_strength = strength * self.review_boost
        return min(new_strength, self.max_strength)

    def get_next_review_time(self, last_review: float, strength: float, threshold: float = 0.8) -> float:
        """计算下次复习时间(保持率降到threshold时)"""
        # R = e^(-t/S) => t = -S * ln(R)
        hours_until = -strength * math.log(threshold)
        return last_review + hours_until * 3600


# ============================================================================
# 知识图谱
# ============================================================================

@dataclass
class Entity:
    """知识图谱实体"""
    name: str
    type: str  # person, place, concept, event, etc.
    mentions: int = 0
    related_pages: Set[str] = field(default_factory=set)


@dataclass
class Relation:
    """实体关系"""
    source: str
    target: str
    relation_type: str
    weight: float = 1.0


class KnowledgeGraph:
    """轻量级知识图谱"""

    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.relations: List[Relation] = []
        self.entity_index: Dict[str, List[str]] = defaultdict(list)  # 实体名 -> 关系索引

    def extract_entities(self, text: str, page_id: str) -> List[str]:
        """从文本中提取实体(简单规则版)"""
        entities_found = []

        # 1. 提取大写开头的英文词组(专有名词)
        english_entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)
        for ent in english_entities:
            if len(ent) > 2:
                entities_found.append((ent, 'concept'))

        # 2. 提取中文中常见的实体模式(简单版)
        # 提取"XX是XX"、"XX叫做XX"等模式
        patterns = [
            r'([\u4e00-\u9fff]{2,10})是',
            r'([\u4e00-\u9fff]{2,10})叫做',
            r'([\u4e00-\u9fff]{2,10})指的是',
            r'([\u4e00-\u9fff]{2,10})是指',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                entities_found.append((match, 'concept'))

        # 3. 提取数字+单位(事件/数据实体)
        number_patterns = re.findall(r'(\d+(?:\.\d+)?)\s*[%%倍个年日月分钟秒]', text)
        for num in number_patterns:
            entities_found.append((f"数值:{num}", 'data'))

        # 去重并添加
        unique_entities = {}
        for name, etype in entities_found:
            if name not in unique_entities:
                unique_entities[name] = etype

        for name, etype in unique_entities.items():
            self._add_entity(name, etype, page_id)

        return list(unique_entities.keys())

    def _add_entity(self, name: str, etype: str, page_id: str):
        """添加实体"""
        if name not in self.entities:
            self.entities[name] = Entity(name=name, type=etype)

        entity = self.entities[name]
        entity.mentions += 1
        entity.related_pages.add(page_id)

    def add_relation(self, source: str, target: str, relation_type: str, weight: float = 1.0):
        """添加实体关系"""
        if source not in self.entities or target not in self.entities:
            return

        relation = Relation(source=source, target=target, relation_type=relation_type, weight=weight)
        self.relations.append(relation)

        idx = len(self.relations) - 1
        self.entity_index[source].append(idx)
        self.entity_index[target].append(idx)

    def get_related_entities(self, entity_name: str, depth: int = 1) -> Dict[str, float]:
        """获取相关实体(带权重)"""
        if entity_name not in self.entities:
            return {}

        visited = {entity_name: 1.0}
        current_level = {entity_name: 1.0}

        for _ in range(depth):
            next_level = defaultdict(float)
            for entity, base_weight in current_level.items():
                for rel_idx in self.entity_index.get(entity, []):
                    rel = self.relations[rel_idx]
                    other = rel.target if rel.source == entity else rel.source
                    if other not in visited:
                        next_level[other] = max(next_level[other], base_weight * rel.weight * 0.7)

            for entity, weight in next_level.items():
                if entity not in visited:
                    visited[entity] = weight

            current_level = next_level
            if not current_level:
                break

        del visited[entity_name]
        return visited

    def get_entity_pages(self, entity_name: str) -> Set[str]:
        """获取实体关联的页面"""
        if entity_name in self.entities:
            return self.entities[entity_name].related_pages
        return set()

    def search_entities(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """搜索实体"""
        query_lower = query.lower()
        scores = []

        for name, entity in self.entities.items():
            if query_lower in name.lower():
                # 匹配度评分
                score = 1.0 if name.lower() == query_lower else 0.7
                score += min(entity.mentions / 10.0, 0.3)
                scores.append((name, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ============================================================================
# 记忆激活传播
# ============================================================================

class ActivationSpreader:
    """记忆激活传播算法(类似扩散激活)"""

    def __init__(self, decay: float = 0.7, steps: int = 3):
        self.decay = decay  # 激活衰减系数
        self.steps = steps  # 传播步数

    def spread(self, start_nodes: Dict[str, float], adjacency: Dict[str, List[Tuple[str, float]]]) -> Dict[str, float]:
        """从起始节点开始传播激活

        Args:
            start_nodes: 起始节点及其初始激活值
            adjacency: 邻接表 {node: [(neighbor, weight), ...]}

        Returns:
            所有节点的激活值
        """
        activation = dict(start_nodes)

        for _ in range(self.steps):
            new_activation = dict(activation)

            for node, act_value in activation.items():
                if act_value < 0.01:
                    continue

                neighbors = adjacency.get(node, [])
                total_weight = sum(w for _, w in neighbors)

                if total_weight == 0:
                    continue

                for neighbor, weight in neighbors:
                    spread_value = act_value * (weight / total_weight) * self.decay
                    new_activation[neighbor] = new_activation.get(neighbor, 0) + spread_value

            activation = new_activation

        return activation


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class MemoryPage:
    """记忆页数据类"""
    page_id: str
    label: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)

    # 时间戳
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)

    # 访问统计
    access_count: int = 0
    version: int = 1

    # 关联指针
    pointers: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    # 状态
    is_deleted: bool = False
    is_distilled: bool = False
    original_page_id: Optional[str] = None

    # v26.0 新增字段
    importance: float = 5.0  # 重要性 0-10
    memory_strength: float = 1.0  # 记忆强度（遗忘曲线用）
    last_reviewed: float = field(default_factory=time.time)  # 上次复习时间
    activation: float = 0.0  # 当前激活值
    entities: List[str] = field(default_factory=list)  # 提取的实体
    vector_hash: str = ""  # 内容向量哈希（用于检测变化）
    content_hash: str = ""  # v26.1: 内容哈希（用于去重）

    # 元数据
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "page_id": self.page_id,
            "label": self.label,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "version": self.version,
            "pointers": dict(self.pointers),
            "is_deleted": self.is_deleted,
            "is_distilled": self.is_distilled,
            "original_page_id": self.original_page_id,
            "importance": self.importance,
            "memory_strength": self.memory_strength,
            "last_reviewed": self.last_reviewed,
            "activation": self.activation,
            "entities": self.entities,
            "content_hash": self.content_hash if hasattr(self, 'content_hash') else "",
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MemoryPage':
        page = cls(
            page_id=data["page_id"],
            label=data["label"],
            content=data["content"],
            category=data.get("category", "misc"),
            tags=data.get("tags", []),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            version=data.get("version", 1),
            is_deleted=data.get("is_deleted", False),
            is_distilled=data.get("is_distilled", False),
            original_page_id=data.get("original_page_id"),
            importance=data.get("importance", 5.0),
            memory_strength=data.get("memory_strength", 1.0),
            last_reviewed=data.get("last_reviewed", time.time()),
            activation=data.get("activation", 0.0),
            entities=data.get("entities", []),
            metadata=data.get("metadata", {}),
        )
        page.pointers = defaultdict(list, data.get("pointers", {}))
        return page


@dataclass
class IndexEntry:
    """索引条目"""
    page_id: str
    label: str
    summary: str
    category: str
    tags: List[str]
    importance: float = 5.0


class TLB:
    """转译后备缓冲区 - 加权LRU快表"""

    def __init__(self, size: int = 50, importance_weight: float = 0.3):
        self.size = size
        self.importance_weight = importance_weight
        self.cache = OrderedDict()
        self.evictions = 0  # Alpha 8 fix: TLB 自身淘汰计数(供引擎聚合统计)

    def get(self, page_id: str) -> Optional[dict]:
        """获取页面,命中则移到末尾(最近使用)"""
        if page_id in self.cache:
            self.cache.move_to_end(page_id)
            return self.cache[page_id]
        return None

    def put(self, page_id: str, page_data: dict, importance: float = 5.0):
        """放入页面,超容则淘汰"""
        if page_id in self.cache:
            self.cache.move_to_end(page_id)
            self.cache[page_id] = page_data
            return

        if len(self.cache) >= self.size:
            self._evict()

        self.cache[page_id] = page_data

    def _evict(self):
        """加权淘汰策略 - v26.1: 加入 access_count 考量"""
        if not self.cache:
            return

        if len(self.cache) <= 1:
            return

        scores = []
        position = 0
        for pid, pdata in self.cache.items():
            pos_weight = position / (len(self.cache) - 1)  # 0-1
            imp = pdata.get("importance", 5.0)
            imp_weight = imp / 10.0  # 0-1
            freq = min(pdata.get("access_count", 0), 20) / 20.0  # 0-1, cap at 20

            # 三因子: 位置30% + 重要性30% + 访问频率40%
            score = (0.30 * pos_weight + 0.30 * imp_weight + 0.40 * freq)
            scores.append((pid, score))
            position += 1

        scores.sort(key=lambda x: x[1])
        evict_id = scores[0][0]
        del self.cache[evict_id]
        self.evictions += 1

    def invalidate(self, page_id: str):
        """使某页失效"""
        if page_id in self.cache:
            del self.cache[page_id]

    def clear(self):
        """清空缓存"""
        self.cache.clear()


# ============================================================================
# 读写锁
# ============================================================================

class RWLock:
    """读写锁 - 多读单写"""

    def __init__(self):
        self._read_ready = threading.Condition(threading.Lock())
        self._readers = 0
        self._writer = False

    def read_acquire(self):
        self._read_ready.acquire()
        try:
            while self._writer:
                self._read_ready.wait()
            self._readers += 1
        finally:
            self._read_ready.release()

    def read_release(self):
        self._read_ready.acquire()
        try:
            self._readers -= 1
            if self._readers == 0:
                self._read_ready.notify_all()
        finally:
            self._read_ready.release()

    def write_acquire(self):
        self._read_ready.acquire()
        while self._readers > 0 or self._writer:
            self._read_ready.wait()
        self._writer = True
        self._read_ready.release()

    def write_release(self):
        self._read_ready.acquire()
        self._writer = False
        self._read_ready.notify_all()
        self._read_ready.release()

    def read(self):
        return _ReadLockContext(self)

    def write(self):
        return _WriteLockContext(self)


class _ReadLockContext:
    def __init__(self, rwlock):
        self.rwlock = rwlock
    def __enter__(self):
        self.rwlock.read_acquire()
    def __exit__(self, *args):
        self.rwlock.read_release()


class _WriteLockContext:
    def __init__(self, rwlock):
        self.rwlock = rwlock
    def __enter__(self):
        self.rwlock.write_acquire()
    def __exit__(self, *args):
        self.rwlock.write_release()


# ============================================================================
# 事务支持
# ============================================================================

class Transaction:
    """记忆事务"""

    def __init__(self, engine):
        self.engine = engine
        self._snapshot = None
        self._active = False

    def begin(self):
        if self._active:
            raise RuntimeError("Transaction already active")
        # 深拷贝快照
        import copy
        self._snapshot = copy.deepcopy({
            "pages": {k: v.to_dict() for k, v in self.engine.pages.items()},
            "index": dict(self.engine.root_index),
        })
        self._active = True

    def commit(self):
        if not self._active:
            raise RuntimeError("No active transaction")
        self._snapshot = None
        self._active = False

    def rollback(self):
        if not self._active:
            raise RuntimeError("No active transaction")
        # 恢复快照
        self.engine.pages = {k: MemoryPage.from_dict(v) for k, v in self._snapshot["pages"].items()}
        self.engine.root_index = self._snapshot["index"]
        self._snapshot = None
        self._active = False

    def __enter__(self):
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        return False


# ============================================================================
# 主引擎
# ============================================================================

class OxygenMemo:
    """
    OxygenMemo v26.0 Alpha 8 - 高级记忆管理引擎
    GitHub@StarsailsClover
    """

    VERSION = "26.0.0-alpha.8"

    def __init__(self, storage_path: str = "./oxygen_memo_data",
                 tlb_size: int = 50,
                 lazy_load: bool = False,
                 max_memory_mb: int = 512,
                 enable_vector_search: bool = True,
                 enable_forgetting: bool = True,
                 enable_knowledge_graph: bool = True,
                 enable_activation: bool = True):

        self.storage_path = storage_path
        self.max_memory_mb = max_memory_mb
        self.lazy_load = lazy_load

        # 功能开关
        self.enable_vector_search = enable_vector_search
        self.enable_forgetting = enable_forgetting
        self.enable_knowledge_graph = enable_knowledge_graph
        self.enable_activation = enable_activation

        # 核心数据结构
        self.pages: Dict[str, MemoryPage] = {}
        self.root_index: Dict[str, Dict] = {}

        # v26.0 新增组件
        if enable_vector_search:
            self.vector_engine = VectorSearchEngine()
        if enable_forgetting:
            self.forgetting_curve = ForgettingCurve()
        if enable_knowledge_graph:
            self.knowledge_graph = KnowledgeGraph()
        if enable_activation:
            self.activation_spreader = ActivationSpreader()

        # TLB缓存
        self.tlb = TLB(size=tlb_size)

        # 并发锁
        self._lock = RWLock()

        # 统计信息
        self._stats = {
            "total_writes": 0,
            "total_reads": 0,
            "tlb_hits": 0,
            "tlb_misses": 0,
            "page_evictions": 0,
            "distilled_pages": 0,
            "loaded_pages": 0,
        }

        # 脏标记
        self._index_dirty = False
        self._pages_dirty: Set[str] = set()

        # v26.1: 内容去重哈希
        self._content_hashes: Dict[str, str] = {}  # hash -> page_id

        # 初始化存储
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "pages"), exist_ok=True)

        # 加载已有数据
        self._load_index()
        if not lazy_load:
            self._load_all_pages()

        # 初始化向量引擎
        if enable_vector_search:
            self._init_vector_engine()

        # 初始化知识图谱
        if enable_knowledge_graph:
            self._init_knowledge_graph()

    # v26.1 优化方法

    def _content_hash(self, content: str) -> str:
        """内容哈希,用于去重"""
        return hashlib.md5(content.strip().encode()).hexdigest()[:16]

    def _generate_summary(self, content: str, max_len: int = 100) -> str:
        """v26.1: 语义摘要 - 提取首句+末句+核心长句"""
        content = content.strip()
        if len(content) <= max_len:
            return content
        sentences = re.split(r'(?<=[。!?\n.!?])\s*', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 3:
            return sentences[0][:max_len]
        parts = [sentences[0], sentences[-1]]
        if len(sentences) > 2:
            mid = max(sentences[1:-1], key=len)
            parts.insert(1, mid)
        summary = " ".join(parts)
        if len(summary) > max_len:
            summary = summary[:max_len - 3] + "..."
        return summary

    # ------------------------------------------------------------------------
    # 持久化相关
    # ------------------------------------------------------------------------

    def _index_path(self) -> str:
        return os.path.join(self.storage_path, "index.json")

    def _page_path(self, page_id: str) -> str:
        return os.path.join(self.storage_path, "pages", f"{page_id}.json")

    def _save_index(self):
        """保存索引(增量:仅脏标记时保存)"""
        if not self._index_dirty:
            return

        index_data = {
            "version": self.VERSION,
            "root_index": self.root_index,
            "stats": self._stats,
        }

        tmp_path = self._index_path() + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._index_path())
            self._index_dirty = False
        except Exception as e:
            print(f"Warning: Failed to save index: {e}")

    def _save_page(self, page_id: str):
        """保存单个页面"""
        if page_id not in self._pages_dirty:
            return

        page = self.pages.get(page_id)
        if not page:
            return

        page_path = self._page_path(page_id)
        tmp_path = page_path + ".tmp"
        try:
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(page.to_dict(), f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, page_path)
            self._pages_dirty.discard(page_id)
        except Exception as e:
            print(f"Warning: Failed to save page {page_id}: {e}")

    def _save_all(self):
        """保存所有脏数据"""
        self._save_index()
        for page_id in list(self._pages_dirty):
            self._save_page(page_id)

    def _load_index(self):
        """加载索引"""
        index_path = self._index_path()
        if not os.path.exists(index_path):
            self._init_default_index()
            return

        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.root_index = data.get("root_index", {})
            self._stats.update(data.get("stats", {}))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Index file corrupted, reinitializing: {e}")
            self._init_default_index()

    def _load_all_pages(self):
        """加载所有页面"""
        pages_dir = os.path.join(self.storage_path, "pages")
        if not os.path.exists(pages_dir):
            return

        for filename in os.listdir(pages_dir):
            if not filename.endswith('.json'):
                continue

            page_id = filename[:-5]  # 去掉 .json
            self._load_page(page_id)

    def _load_page(self, page_id: str) -> Optional[MemoryPage]:
        """加载单个页面"""
        page_path = self._page_path(page_id)
        if not os.path.exists(page_path):
            return None

        try:
            with open(page_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            page = MemoryPage.from_dict(data)
            self.pages[page_id] = page
            # Alpha 7 fix: use content_hash (not vector_hash) for dedup mapping
            if hasattr(page, 'content_hash') and page.content_hash:
                self._content_hashes[page.content_hash] = page_id
            self._stats["loaded_pages"] = len(self.pages)
            return page
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load page {page_id}: {e}")
            return None

    def _get_page_internal(self, page_id: str) -> Optional[MemoryPage]:
        """内部获取页面(先查 TLB 快表,再回落到内存/磁盘)"""
        # Alpha 8 fix: 先查询 TLB,使 tlb_hits/tlb_misses 真正生效
        cached = self.tlb.get(page_id)
        if cached is not None:
            self._stats["tlb_hits"] += 1
            page = self.pages.get(page_id)
            if page is not None:
                # 内存中的对象为权威副本,直接返回
                return page
            # 懒加载模式下内存已换出,用缓存的 dict 重建页对象
            page = MemoryPage.from_dict(cached)
            self.pages[page_id] = page
            return page

        # TLB 未命中
        self._stats["tlb_misses"] += 1
        page = self.pages.get(page_id)

        if page is None and self.lazy_load:
            # 懒加载:从磁盘加载
            page = self._load_page(page_id)

        # 命中内存/磁盘后回填 TLB(dict 形式,保持一致)
        if page is not None:
            self.tlb.put(page_id, page.to_dict(), page.importance)

        return page

    def _init_default_index(self):
        """初始化默认索引结构"""
        self.root_index = {
            "core": {"label": "核心背景", "children": {}},
            "task": {"label": "任务进度", "children": {}},
            "knowledge": {"label": "知识沉淀", "children": {}},
            "history": {"label": "交互历史", "children": {}},
            "misc": {"label": "其他", "children": {}},
        }
        self._index_dirty = True

    def _init_vector_engine(self):
        """初始化向量搜索引擎"""
        for page_id, page in self.pages.items():
            if not page.is_deleted:
                self.vector_engine.add_document(page_id, page.content)

    def _init_knowledge_graph(self):
        """初始化知识图谱"""
        for page_id, page in self.pages.items():
            if not page.is_deleted:
                entities = self.knowledge_graph.extract_entities(page.content, page_id)
                # Alpha 8 fix: 加载已有数据时重建实体共现关系
                self._link_cooccurring_entities(entities)

    def _link_cooccurring_entities(self, entities: List[str], relation_type: str = "co_occurs"):
        """Alpha 8: 为同一上下文中共现的实体建立关系(带去重,避免关系爆炸)

        限制每次最多处理前若干实体,防止长文本产生 O(n^2) 关系。
        """
        if not self.enable_knowledge_graph:
            return

        # 去重并保序
        unique = []
        seen = set()
        for e in entities:
            if e and e not in seen:
                seen.add(e)
                unique.append(e)

        # 限制规模,避免关系数量爆炸
        unique = unique[:8]
        if len(unique) < 2:
            return

        # 已存在的关系对(无向)用于去重
        existing_pairs = set()
        for rel in self.knowledge_graph.relations:
            existing_pairs.add(frozenset((rel.source, rel.target)))

        for i in range(len(unique)):
            for j in range(i + 1, len(unique)):
                pair = frozenset((unique[i], unique[j]))
                if pair in existing_pairs:
                    continue
                self.knowledge_graph.add_relation(unique[i], unique[j], relation_type)
                existing_pairs.add(pair)

    # ------------------------------------------------------------------------
    # 基础读写
    # ------------------------------------------------------------------------

    def write_page(self, content: str, label: str, category: str = "misc",
                   page_id: Optional[str] = None, tags: Optional[List[str]] = None,
                   importance: Optional[float] = None) -> str:
        """写入记忆页"""
        with self._lock.write():
            return self._write_page_internal(content, label, category, page_id, tags, importance)

    def _write_page_internal(self, content: str, label: str, category: str = "misc",
                             page_id: Optional[str] = None, tags: Optional[List[str]] = None,
                             importance: Optional[float] = None) -> str:
        """内部写入(不加锁)"""

        # v26.1: 内容去重检查（仅未指定 page_id 时）
        content_hash = self._content_hash(content)
        if content_hash in self._content_hashes and page_id is None:
            existing_id = self._content_hashes[content_hash]
            existing = self._get_page_internal(existing_id)
            if existing and not existing.is_deleted:
                existing.label = label
                existing.last_accessed = time.time()
                existing.access_count += 1
                existing.content_hash = content_hash
                self._update_index(existing)
                self._index_dirty = True
                self._pages_dirty.add(existing_id)  # Alpha 8: 标记脏以持久化更新
                self._save_page(existing_id)  # Alpha 8 fix: 传 page_id 而非对象
                # Alpha 8 fix: tlb.put 需要 (page_id, page_data, importance)
                self.tlb.put(existing_id, existing.to_dict(), existing.importance)
                return existing_id

        # 确定页面ID
        if page_id is None:
            page_id = self._generate_page_id(category)

        # 检查是否已存在(更新)
        existing = self._get_page_internal(page_id)

        if existing:
            # 写时复制
            existing.content = content
            existing.label = label
            existing.category = category
            existing.updated_at = time.time()
            existing.version += 1
            if tags is not None:
                existing.tags = tags
            if importance is not None:
                existing.importance = importance

            page = existing
        else:
            # 新建页面
            page = MemoryPage(
                page_id=page_id,
                label=label,
                content=content,
                category=category,
                tags=tags or [],
                importance=importance if importance is not None else 5.0,
            )
            page.content_hash = content_hash  # Alpha 8 fix: 持久化内容哈希以支持跨会话去重
            self.pages[page_id] = page
            self._content_hashes[content_hash] = page_id

        # 更新索引
        self._update_index(page)

        # 更新向量引擎
        if self.enable_vector_search:
            if existing:
                self.vector_engine.update_document(page_id, content)
            else:
                self.vector_engine.add_document(page_id, content)

        # 更新知识图谱
        if self.enable_knowledge_graph:
            entities = self.knowledge_graph.extract_entities(content, page_id)
            page.entities = entities
            # Alpha 8 fix: 为同页共现的实体建立关系,使关系图谱非空且可查询
            self._link_cooccurring_entities(entities)

        # 标记脏
        self._index_dirty = True
        self._pages_dirty.add(page_id)

        # 更新统计
        self._stats["total_writes"] += 1

        # 检查内存限制
        self._check_memory_limit()

        # 自动保存(可选,这里先不自动保存,由调用方控制)

        return page_id

    def _generate_page_id(self, category: str) -> str:
        """生成页面ID"""
        prefix_map = {
            "core": "C",
            "task": "T",
            "knowledge": "K",
            "history": "H",
            "misc": "M",
        }
        prefix = prefix_map.get(category, "M")

        # 找到最大序号
        max_num = 0
        for pid in self.pages.keys():
            if pid.startswith(prefix):
                try:
                    num = int(pid[1:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass

        return f"{prefix}{max_num + 1:03d}"

    def _update_index(self, page: MemoryPage):
        """更新索引"""
        category = page.category
        if category not in self.root_index:
            self.root_index[category] = {"label": category, "children": {}}

        self.root_index[category]["children"][page.page_id] = {
            "label": page.label,
            "summary": self._generate_summary(page.content),
            "tags": page.tags,
            "importance": page.importance,
        }

    def load_page(self, page_id: str) -> Optional[dict]:
        """读取记忆页"""
        with self._lock.read():
            page = self._get_page_internal(page_id)

            if page is None or page.is_deleted:
                return None

            # 更新访问统计
            page.access_count += 1
            page.last_accessed = time.time()

            # 更新记忆强度(访问相当于复习)
            if self.enable_forgetting:
                page.memory_strength = self.forgetting_curve.review(page.memory_strength)
                page.last_reviewed = time.time()

            # 更新TLB
            self.tlb.put(page_id, page.to_dict(), page.importance)

            # 更新统计
            self._stats["total_reads"] += 1

            # 标记脏(因为更新了访问计数)
            self._pages_dirty.add(page_id)

            return page.to_dict()

    def append_page(self, page_id: str, content: str) -> bool:
        """追加内容到页面"""
        with self._lock.write():
            page = self._get_page_internal(page_id)
            if page is None or page.is_deleted:
                return False

            page.content += "\n" + content
            page.updated_at = time.time()
            page.version += 1

            # 更新向量引擎
            if self.enable_vector_search:
                self.vector_engine.update_document(page_id, page.content)

            # 更新知识图谱
            if self.enable_knowledge_graph:
                new_entities = self.knowledge_graph.extract_entities(content, page_id)
                page.entities = list(set(page.entities + new_entities))
                # Alpha 8 fix: 为同页共现的实体建立关系
                self._link_cooccurring_entities(page.entities)

            self._update_index(page)
            self._index_dirty = True
            self._pages_dirty.add(page_id)

            return True

    def delete_page(self, page_id: str, permanent: bool = False) -> bool:
        """删除页面"""
        with self._lock.write():
            return self._delete_page_internal(page_id, permanent)

    def _delete_page_internal(self, page_id: str, permanent: bool = False) -> bool:
        """删除页面(内部方法,不加锁 - 供已持有写锁的调用方复用,避免 RWLock 非重入死锁)"""
        page = self._get_page_internal(page_id)
        if page is None:
            return False

        if permanent:
            # 永久删除
            del self.pages[page_id]
            if page.category in self.root_index:
                self.root_index[page.category]["children"].pop(page_id, None)

            if self.enable_vector_search:
                self.vector_engine.remove_document(page_id)

            page_path = self._page_path(page_id)
            if os.path.exists(page_path):
                os.remove(page_path)
        else:
            # 软删除
            page.is_deleted = True
            page.updated_at = time.time()
            self._pages_dirty.add(page_id)

        self.tlb.invalidate(page_id)
        if hasattr(page, 'content_hash') and page.content_hash:
            self._content_hashes.pop(page.content_hash, None)
        self._index_dirty = True

        return True

    # ------------------------------------------------------------------------
    # v26.0 新增:向量语义搜索
    # ------------------------------------------------------------------------

    def semantic_search(self, query: str, top_k: int = 10,
                        min_score: float = 0.1,
                        category: Optional[str] = None) -> List[Dict]:
        """语义搜索记忆页

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            min_score: 最小相似度阈值
            category: 可选分类过滤

        Returns:
            搜索结果列表,包含page_id, label, score, snippet
        """
        if not self.enable_vector_search:
            return []

        with self._lock.read():
            results = self.vector_engine.search(query, top_k * 2)

            filtered = []
            for page_id, score in results:
                if score < min_score:
                    continue

                page = self._get_page_internal(page_id)
                if page is None or page.is_deleted:
                    continue

                if category and page.category != category:
                    continue

                # 生成摘要片段
                snippet = self._extract_snippet(page.content, query)

                filtered.append({
                    "page_id": page_id,
                    "label": page.label,
                    "score": round(score, 4),
                    "category": page.category,
                    "snippet": snippet,
                    "importance": page.importance,
                })

                if len(filtered) >= top_k:
                    break

            return filtered

    def _extract_snippet(self, content: str, query: str, context_chars: int = 50) -> str:
        """提取相关片段"""
        query_lower = query.lower()
        content_lower = content.lower()

        pos = content_lower.find(query_lower)
        if pos == -1:
            # 没找到就返回开头
            return content[:100] + "..." if len(content) > 100 else content

        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(query) + context_chars)

        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet

    def find_similar_pages(self, page_id: str, top_k: int = 5) -> List[Dict]:
        """查找相似页面"""
        if not self.enable_vector_search:
            return []

        with self._lock.read():
            similar = self.vector_engine.get_similar(page_id, top_k)

            results = []
            for sim_id, score in similar:
                page = self._get_page_internal(sim_id)
                if page and not page.is_deleted:
                    results.append({
                        "page_id": sim_id,
                        "label": page.label,
                        "similarity": round(score, 4),
                        "category": page.category,
                    })

            return results

    # ------------------------------------------------------------------------
    # v26.0 新增:遗忘曲线与记忆复习
    # ------------------------------------------------------------------------

    def get_memory_retention(self, page_id: str) -> Optional[float]:
        """获取页面的记忆保持率"""
        if not self.enable_forgetting:
            return None

        with self._lock.read():
            page = self._get_page_internal(page_id)
            if page is None or page.is_deleted:
                return None

            return self.forgetting_curve.calculate_retention(
                page.last_reviewed, page.memory_strength
            )

    def review_page(self, page_id: str) -> bool:
        """复习页面(增强记忆强度)"""
        if not self.enable_forgetting:
            return False

        with self._lock.write():
            page = self._get_page_internal(page_id)
            if page is None or page.is_deleted:
                return False

            page.memory_strength = self.forgetting_curve.review(page.memory_strength)
            page.last_reviewed = time.time()
            self._pages_dirty.add(page_id)

            return True

    def get_pages_needing_review(self, threshold: float = 0.7,
                                 limit: int = 20) -> List[Dict]:
        """获取需要复习的页面(保持率低于阈值)"""
        if not self.enable_forgetting:
            return []

        with self._lock.read():
            needs_review = []

            for page_id, page in self.pages.items():
                if page is None or page.is_deleted:
                    continue

                retention = self.forgetting_curve.calculate_retention(
                    page.last_reviewed, page.memory_strength
                )

                if retention < threshold:
                    needs_review.append({
                        "page_id": page_id,
                        "label": page.label,
                        "retention": round(retention, 4),
                        "strength": round(page.memory_strength, 2),
                        "importance": page.importance,
                    })

            # 按保持率排序(最需要复习的在前)
            needs_review.sort(key=lambda x: x["retention"])
            return needs_review[:limit]

    # ------------------------------------------------------------------------
    # v26.0 新增:知识图谱
    # ------------------------------------------------------------------------

    def search_entities(self, query: str, top_k: int = 10) -> List[Dict]:
        """搜索知识图谱实体"""
        if not self.enable_knowledge_graph:
            return []

        with self._lock.read():
            results = self.knowledge_graph.search_entities(query, top_k)

            enriched = []
            for name, score in results:
                entity = self.knowledge_graph.entities.get(name)
                if entity:
                    enriched.append({
                        "name": name,
                        "type": entity.type,
                        "mentions": entity.mentions,
                        "related_pages": len(entity.related_pages),
                        "score": round(score, 4),
                    })

            return enriched

    def get_entity_pages(self, entity_name: str) -> List[Dict]:
        """获取与实体相关的页面"""
        if not self.enable_knowledge_graph:
            return []

        with self._lock.read():
            page_ids = self.knowledge_graph.get_entity_pages(entity_name)

            pages = []
            for pid in page_ids:
                page = self._get_page_internal(pid)
                if page and not page.is_deleted:
                    pages.append({
                        "page_id": pid,
                        "label": page.label,
                        "category": page.category,
                    })

            return pages

    def get_related_entities(self, entity_name: str, depth: int = 1) -> List[Dict]:
        """获取相关实体"""
        if not self.enable_knowledge_graph:
            return []

        with self._lock.read():
            related = self.knowledge_graph.get_related_entities(entity_name, depth)

            results = []
            for name, weight in sorted(related.items(), key=lambda x: x[1], reverse=True):
                entity = self.knowledge_graph.entities.get(name)
                if entity:
                    results.append({
                        "name": name,
                        "type": entity.type,
                        "relevance": round(weight, 4),
                    })

            return results

    # ------------------------------------------------------------------------
    # v26.0 新增:激活传播
    # ------------------------------------------------------------------------

    def activate_memory(self, query: str, top_k: int = 20) -> List[Dict]:
        """基于查询激活相关记忆(扩散激活)

        结合语义搜索和知识图谱进行激活传播
        """
        if not self.enable_activation or not self.enable_vector_search:
            return self.semantic_search(query, top_k)

        with self._lock.read():
            # 1. 语义搜索获取初始激活节点
            initial_results = self.vector_engine.search(query, top_k)

            if not initial_results:
                return []

            # 2. 构建邻接表(基于指针和相似性)
            adjacency = {}
            for page_id, _ in initial_results:
                page = self._get_page_internal(page_id)
                if page is None:
                    continue

                neighbors = []

                # 指针关联
                for rel_type, targets in page.pointers.items():
                    for target in targets:
                        neighbors.append((target, 0.8))

                # 相似页面(如果启用了向量搜索)
                if self.enable_vector_search:
                    similar = self.vector_engine.get_similar(page_id, 3)
                    for sim_id, sim_score in similar:
                        neighbors.append((sim_id, sim_score * 0.5))

                adjacency[page_id] = neighbors

            # 3. 初始激活
            start_activation = {pid: score for pid, score in initial_results}

            # 4. 传播激活
            final_activation = self.activation_spreader.spread(start_activation, adjacency)

            # 5. 返回结果
            results = []
            for page_id, act_value in sorted(final_activation.items(), key=lambda x: x[1], reverse=True):
                page = self._get_page_internal(page_id)
                if page is None or page.is_deleted:
                    continue

                results.append({
                    "page_id": page_id,
                    "label": page.label,
                    "activation": round(act_value, 4),
                    "category": page.category,
                    "importance": page.importance,
                })

                if len(results) >= top_k:
                    break

            return results

    # ------------------------------------------------------------------------
    # v26.0 新增:记忆巩固(睡眠整合)
    # ------------------------------------------------------------------------

    def consolidate_memory(self) -> Dict:
        """记忆巩固(类似睡眠中的记忆整合)

        功能:
        1. 识别高频访问的重要记忆
        2. 合并相似记忆
        3. 强化重要关联
        4. 蒸馏低价值记忆
        5. 清理遗忘的记忆

        Returns:
            巩固统计信息
        """
        with self._lock.write():
            stats = {
                "pages_analyzed": 0,
                "similar_merged": 0,
                "distilled": 0,
                "forgotten": 0,
                "strengthened": 0,
            }

            # 1. 分析所有页面
            active_pages = []
            for page_id, page in self.pages.items():
                if page is None or page.is_deleted:
                    continue
                stats["pages_analyzed"] += 1

                # 计算综合价值
                value = (
                    page.importance * 0.4 +
                    min(page.access_count / 10.0, 1.0) * 0.3 +
                    page.memory_strength / 10.0 * 0.3
                )

                active_pages.append((page_id, value, page))

            # 2. 低价值且遗忘率高的页面进行蒸馏或遗忘
            for page_id, value, page in active_pages:
                if value < 2.0 and self.enable_forgetting:
                    retention = self.forgetting_curve.calculate_retention(
                        page.last_reviewed, page.memory_strength
                    )
                    if retention < 0.3:
                        # 深度遗忘,考虑蒸馏
                        if not page.is_distilled and len(page.content) > 200:
                            self._distill_page_inplace(page_id)
                            stats["distilled"] += 1
                        elif retention < 0.1 and value < 1.0:
                            # 几乎完全遗忘,标记为删除
                            page.is_deleted = True
                            self._pages_dirty.add(page_id)  # Alpha 8 fix: 标记脏
                            stats["forgotten"] += 1

                # 高价值页面增强记忆强度
                if value > 7.0 and self.enable_forgetting:
                    page.memory_strength = min(page.memory_strength * 1.2, 10.0)
                    self._pages_dirty.add(page_id)  # Alpha 8 fix: 标记脏
                    stats["strengthened"] += 1

            # 3. 合并高度相似的页面(简单版)
            if self.enable_vector_search and len(active_pages) > 10:
                # 只合并低价值的相似页面
                low_value_pages = [(pid, p) for pid, val, p in active_pages if val < 4.0]

                merged = set()
                for i, (pid1, page1) in enumerate(low_value_pages):
                    if pid1 in merged:
                        continue

                    similar = self.vector_engine.get_similar(pid1, 3)
                    for sim_id, sim_score in similar:
                        if sim_id in merged or sim_id == pid1:
                            continue

                        if sim_score > 0.8:  # 高度相似
                            # 合并到第一个页面
                            page2 = self._get_page_internal(sim_id)
                            if page2:
                                page1.content += "\n\n--- 合并自 " + page2.label + " ---\n" + page2.content
                                page1.updated_at = time.time()
                                page2.is_deleted = True
                                merged.add(sim_id)
                                stats["similar_merged"] += 1
                                # Alpha 8 fix: 标记两个页面为脏以持久化合并结果
                                self._pages_dirty.add(pid1)
                                self._pages_dirty.add(sim_id)

                                if self.enable_vector_search:
                                    self.vector_engine.update_document(pid1, page1.content)

            self._index_dirty = True
            return stats

    # ------------------------------------------------------------------------
    # 指针与关联
    # ------------------------------------------------------------------------

    def create_pointer(self, source_id: str, target_id: str, relation_type: str = "related") -> bool:
        """创建记忆指针"""
        with self._lock.write():
            source = self._get_page_internal(source_id)
            target = self._get_page_internal(target_id)

            if source is None or target is None:
                return False

            if relation_type not in source.pointers:
                source.pointers[relation_type] = []

            if target_id not in source.pointers[relation_type]:
                source.pointers[relation_type].append(target_id)
                self._pages_dirty.add(source_id)

            # Alpha 8 fix: 页面显式关联时,连接两页的实体到知识图谱
            if self.enable_knowledge_graph:
                self._link_cooccurring_entities(source.entities + target.entities, relation_type)

            return True

    def get_related_pages(self, page_id: str, relation_type: Optional[str] = None) -> List[dict]:
        """获取关联页面"""
        with self._lock.read():
            page = self._get_page_internal(page_id)
            if page is None:
                return []

            related = []

            if relation_type:
                targets = page.pointers.get(relation_type, [])
            else:
                targets = []
                for tgts in page.pointers.values():
                    targets.extend(tgts)

            for target_id in targets:
                target = self._get_page_internal(target_id)
                if target and not target.is_deleted:
                    related.append(target.to_dict())

            return related

    def merge_pages(self, page_ids: List[str], new_label: str, category: Optional[str] = None) -> str:
        """合并多个页面"""
        with self._lock.write():
            if len(page_ids) < 2:
                raise ValueError("Need at least 2 pages to merge")

            # 收集内容
            contents = []
            categories = set()
            all_tags = set()

            for pid in page_ids:
                page = self._get_page_internal(pid)
                if page and not page.is_deleted:
                    contents.append(f"## {page.label}\n\n{page.content}")
                    categories.add(page.category)
                    all_tags.update(page.tags)

            if not contents:
                raise ValueError("No valid pages to merge")

            merged_content = "\n\n---\n\n".join(contents)
            merged_category = category or list(categories)[0]

            # 创建新页面
            new_id = self._write_page_internal(
                merged_content, new_label, merged_category,
                tags=list(all_tags)
            )

            # 标记原页面为已合并(软删除)
            for pid in page_ids:
                page = self._get_page_internal(pid)
                if page:
                    page.is_deleted = True
                    self._pages_dirty.add(pid)

            return new_id

    # ------------------------------------------------------------------------
    # 记忆蒸馏
    # ------------------------------------------------------------------------

    def distill_page(self, page_id: str, ratio: float = 0.5,
                     replace_original: bool = False) -> Optional[str]:
        """记忆蒸馏:压缩提炼页面内容

        Args:
            page_id: 页面ID
            ratio: 压缩比例(保留多少)
            replace_original: 是否替换原始页面(真正节省空间)

        Returns:
            新页面ID或原页面ID
        """
        with self._lock.write():
            page = self._get_page_internal(page_id)
            if page is None or page.is_deleted:
                return None

            # 提取关键词
            keywords = self._extract_keywords(page.content)

            # 分句
            sentences = re.split(r'[。!?.!?\n]+', page.content)
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                return None

            # 句子打分
            scored_sentences = []
            for i, sent in enumerate(sentences):
                score = 0.0

                # 关键词命中分
                sent_lower = sent.lower()
                keyword_hits = sum(1 for kw in keywords if kw in sent_lower)
                score += keyword_hits * 0.5

                # 位置分(首句、末句加分)
                if i == 0:
                    score += 2.0
                elif i == len(sentences) - 1:
                    score += 1.0

                # 长度分(适中长度的句子更重要)
                length = len(sent)
                if 20 < length < 200:
                    score += 1.0

                scored_sentences.append((sent, score, i))

            # 按分数排序,选择Top N
            scored_sentences.sort(key=lambda x: x[1], reverse=True)
            keep_count = max(1, int(len(sentences) * ratio))
            top_sentences = scored_sentences[:keep_count]

            # 按原顺序排列
            top_sentences.sort(key=lambda x: x[2])
            distilled_content = "。".join(s for s, _, _ in top_sentences) + "。"

            if replace_original:
                # 原地替换
                page.content = distilled_content
                page.is_distilled = True
                page.original_page_id = None  # 原地替换没有原始页
                page.updated_at = time.time()
                page.version += 1

                # 更新向量引擎
                if self.enable_vector_search:
                    self.vector_engine.update_document(page_id, distilled_content)

                self._update_index(page)
                self._index_dirty = True
                self._pages_dirty.add(page_id)
                self._stats["distilled_pages"] += 1

                return page_id
            else:
                # 创建新的蒸馏页
                distilled_id = self._write_page_internal(
                    distilled_content,
                    f"[蒸馏] {page.label}",
                    page.category,
                    importance=page.importance * 0.8,  # 蒸馏版重要性降低
                    tags=page.tags + ["distilled"],
                )

                # 设置关联
                new_page = self.pages[distilled_id]
                new_page.is_distilled = True
                new_page.original_page_id = page_id

                # 创建指针
                if "distilled_from" not in new_page.pointers:
                    new_page.pointers["distilled_from"] = []
                new_page.pointers["distilled_from"].append(page_id)

                if "distilled_to" not in page.pointers:
                    page.pointers["distilled_to"] = []
                page.pointers["distilled_to"].append(distilled_id)

                self._pages_dirty.add(page_id)
                self._stats["distilled_pages"] += 1

                return distilled_id

    def _distill_page_inplace(self, page_id: str) -> bool:
        """原地蒸馏(内部方法,不加锁)"""
        page = self._get_page_internal(page_id)
        if page is None or page.is_deleted or page.is_distilled:
            return False

        keywords = self._extract_keywords(page.content)
        sentences = re.split(r'[。!?.!?\n]+', page.content)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return False

        scored = []
        for i, sent in enumerate(sentences):
            score = 0.0
            sent_lower = sent.lower()
            keyword_hits = sum(1 for kw in keywords if kw in sent_lower)
            score += keyword_hits * 0.5
            if i == 0:
                score += 2.0
            elif i == len(sentences) - 1:
                score += 1.0
            length = len(sent)
            if 20 < length < 200:
                score += 1.0
            scored.append((sent, score, i))

        scored.sort(key=lambda x: x[1], reverse=True)
        keep_count = max(1, int(len(sentences) * 0.5))
        top = scored[:keep_count]
        top.sort(key=lambda x: x[2])

        page.content = "。".join(s for s, _, _ in top) + "。"
        page.is_distilled = True
        page.updated_at = time.time()
        page.version += 1

        if self.enable_vector_search:
            self.vector_engine.update_document(page_id, page.content)

        self._update_index(page)
        self._pages_dirty.add(page_id)
        self._stats["distilled_pages"] += 1

        return True

    def _extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """提取关键词"""
        tokens = tokenize(text)

        # 停用词
        stopwords = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'out', 'off', 'over',
            'under', 'again', 'further', 'then', 'once', 'and', 'but', 'or',
            'nor', 'not', 'so', 'yet', 'both', 'either', 'neither', 'each',
            'every', 'all', 'any', 'few', 'more', 'most', 'other', 'some',
            'such', 'no', 'only', 'own', 'same', 'than', 'too', 'very', 'just',
            '的', '是', '在', '了', '和', '与', '及', '或', '等', '也', '都',
            '就', '而', '但', '还', '又', '再', '更', '最', '这', '那',
            '有', '没', '不', '很', '个', '上', '下', '中', '为', '以',
        }

        # 词频统计
        freq = defaultdict(int)
        for token in tokens:
            if len(token) < 2:
                continue
            if token.lower() in stopwords:
                continue
            freq[token] += 1

        # 排序返回
        sorted_keywords = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_keywords[:top_n]]

    def batch_distill(self, category: Optional[str] = None,
                      min_length: int = 500, ratio: float = 0.5) -> int:
        """批量蒸馏"""
        with self._lock.read():
            # 先收集需要蒸馏的页面ID
            to_distill = []
            for page_id, page in self.pages.items():
                if page is None or page.is_deleted or page.is_distilled:
                    continue
                if category and page.category != category:
                    continue
                if len(page.content) >= min_length:
                    to_distill.append(page_id)

        # 逐个蒸馏(释放读锁后再写,避免锁嵌套)
        count = 0
        for pid in to_distill:
            if self.distill_page(pid, ratio=ratio, replace_original=True):
                count += 1

        return count

    # ------------------------------------------------------------------------
    # 垃圾回收
    # ------------------------------------------------------------------------

    def collect_garbage(self, max_age_days: int = 30,
                        min_access: int = 1,
                        auto_distill: bool = False) -> Dict:
        """垃圾回收"""
        with self._lock.write():
            stats = {
                "deleted": 0,
                "distilled": 0,
                "freed_bytes": 0,
            }

            now = time.time()
            max_age_seconds = max_age_days * 86400

            to_delete = []

            for page_id, page in self.pages.items():
                if page is None or page.is_deleted:
                    continue

                age = now - page.last_accessed
                is_old = age > max_age_seconds
                is_low_access = page.access_count < min_access

                if is_old and is_low_access:
                    if auto_distill and not page.is_distilled and len(page.content) > 200:
                        # 蒸馏而不是删除
                        self._distill_page_inplace(page_id)
                        stats["distilled"] += 1
                    else:
                        to_delete.append(page_id)

            for page_id in to_delete:
                page = self.pages.get(page_id)
                if page:
                    stats["freed_bytes"] += len(page.content.encode('utf-8'))

                # Alpha 8 fix: 已持有写锁,调用非加锁内部删除以避免 RWLock 死锁
                self._delete_page_internal(page_id, permanent=True)
                stats["deleted"] += 1

            return stats

    # ------------------------------------------------------------------------
    # 语义预取
    # ------------------------------------------------------------------------

    def semantic_prefetch(self, current_page_id: str, top_k: int = 5) -> List[str]:
        """语义预取:预加载可能需要的页面"""
        with self._lock.read():
            prefetch_ids = []

            # 1. 基于指针的预取
            page = self._get_page_internal(current_page_id)
            if page:
                for targets in page.pointers.values():
                    prefetch_ids.extend(targets[:3])

            # 2. 基于相似性的预取
            if self.enable_vector_search:
                similar = self.vector_engine.get_similar(current_page_id, 3)
                prefetch_ids.extend([pid for pid, _ in similar])

            # 3. 同分类高访问量页面
            if page:
                same_category = []
                for pid, p in self.pages.items():
                    if p and not p.is_deleted and p.category == page.category and pid != current_page_id:
                        same_category.append((pid, p.access_count))
                same_category.sort(key=lambda x: x[1], reverse=True)
                prefetch_ids.extend([pid for pid, _ in same_category[:2]])

            # 去重并限制数量
            seen = set()
            result = []
            for pid in prefetch_ids:
                if pid not in seen and pid != current_page_id:
                    seen.add(pid)
                    result.append(pid)
                    if len(result) >= top_k:
                        break

            # 加载到TLB
            for pid in result:
                p = self._get_page_internal(pid)
                if p:
                    self.tlb.put(pid, p.to_dict(), p.importance)

            return result

    # ------------------------------------------------------------------------
    # 一致性校验
    # ------------------------------------------------------------------------

    def check_consistency(self) -> Dict:
        """一致性校验"""
        with self._lock.read():
            issues = {
                "orphan_pages": [],  # 孤立页(不在索引中)
                "broken_pointers": [],  # 断链指针
                "duplicate_labels": [],  # 重复标签
                "missing_files": [],  # 缺失文件
                "corrupted_pages": [],  # 损坏页面
            }

            # 检查索引中的页面
            indexed_pages = set()
            for cat_data in self.root_index.values():
                for pid in cat_data.get("children", {}).keys():
                    indexed_pages.add(pid)

            # 检查孤立页
            for page_id in self.pages.keys():
                if page_id not in indexed_pages:
                    page = self._get_page_internal(page_id)
                    if page and not page.is_deleted:
                        issues["orphan_pages"].append(page_id)

            # 检查断链指针
            for page_id, page in self.pages.items():
                if page is None or page.is_deleted:
                    continue

                for rel_type, targets in page.pointers.items():
                    for target_id in targets:
                        target = self._get_page_internal(target_id)
                        if target is None or target.is_deleted:
                            issues["broken_pointers"].append({
                                "source": page_id,
                                "target": target_id,
                                "relation": rel_type,
                            })

            # 检查重复标签
            labels = defaultdict(list)
            for page_id, page in self.pages.items():
                if page and not page.is_deleted:
                    labels[page.label].append(page_id)

            for label, pids in labels.items():
                if len(pids) > 1:
                    issues["duplicate_labels"].append({"label": label, "pages": pids})

            # 统计
            total_pages = sum(1 for p in self.pages.values() if p and not p.is_deleted)
            issue_count = (len(issues["orphan_pages"]) +
                          len(issues["broken_pointers"]) +
                          len(issues["duplicate_labels"]))

            return {
                "total_pages": total_pages,
                "issues_found": issue_count,
                "details": issues,
            }

    # ------------------------------------------------------------------------
    # 健康检查
    # ------------------------------------------------------------------------

    def health_check(self) -> Dict:
        """系统健康检查"""
        with self._lock.read():
            # 基础统计
            total_pages = sum(1 for p in self.pages.values() if p and not p.is_deleted)
            total_content_size = sum(len(p.content.encode('utf-8')) for p in self.pages.values() if p)

            # 一致性检查
            consistency = self.check_consistency()

            # 内存使用估算
            memory_usage_kb = total_content_size / 1024

            # 计算健康评分
            score = 100

            # 扣分:一致性问题
            score -= consistency["issues_found"] * 5

            # 扣分:内存过高
            if self.max_memory_mb and memory_usage_kb > self.max_memory_mb * 1024 * 0.8:
                score -= 20

            # 扣分:蒸馏页比例过高
            distilled_count = sum(1 for p in self.pages.values() if p and p.is_distilled)
            if total_pages > 0 and distilled_count / total_pages > 0.5:
                score -= 10

            score = max(0, min(100, score))

            # 生成建议
            suggestions = []

            if consistency["issues_found"] > 0:
                suggestions.append("存在一致性问题,建议运行修复")

            if memory_usage_kb > self.max_memory_mb * 1024 * 0.7:
                suggestions.append("内存使用率较高,建议执行垃圾回收或蒸馏")

            if self.enable_forgetting:
                needs_review = len(self.get_pages_needing_review(threshold=0.5, limit=100))
                if needs_review > 10:
                    suggestions.append(f"有 {needs_review} 个页面需要复习")

            if total_pages > 100:
                suggestions.append("页面数量较多,建议定期执行记忆巩固")

            return {
                "score": score,
                "total_pages": total_pages,
                "memory_usage_kb": round(memory_usage_kb, 2),
                "distilled_pages": distilled_count,
                "consistency_issues": consistency["issues_found"],
                "suggestions": suggestions,
                "version": self.VERSION,
            }

    # ------------------------------------------------------------------------
    # 统计信息
    # ------------------------------------------------------------------------

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._lock.read():
            total_pages = sum(1 for p in self.pages.values() if p and not p.is_deleted)
            categories = defaultdict(int)
            for p in self.pages.values():
                if p and not p.is_deleted:
                    categories[p.category] += 1

            # Alpha 8 fix: 聚合 TLB 自身淘汰计数 + 内存换页计数
            total_evictions = self._stats.get("page_evictions", 0) + self.tlb.evictions

            return {
                "version": self.VERSION,
                "total_pages": total_pages,
                "categories": dict(categories),
                "total_writes": self._stats["total_writes"],
                "total_reads": self._stats["total_reads"],
                "tlb_hits": self._stats["tlb_hits"],
                "tlb_misses": self._stats["tlb_misses"],
                "page_evictions": total_evictions,
                "tlb_evictions": self.tlb.evictions,
                "loaded_pages": len(self.pages),
                "distilled_pages": self._stats["distilled_pages"],
                "features": {
                    "vector_search": self.enable_vector_search,
                    "forgetting_curve": self.enable_forgetting,
                    "knowledge_graph": self.enable_knowledge_graph,
                    "activation_spread": self.enable_activation,
                },
            }

    # ------------------------------------------------------------------------
    # 批量操作
    # ------------------------------------------------------------------------

    def batch_write_pages(self, pages: List[Dict]) -> List[str]:
        """批量写入页面"""
        with self._lock.write():
            page_ids = []

            for page_data in pages:
                pid = self._write_page_internal(
                    content=page_data["content"],
                    label=page_data["label"],
                    category=page_data.get("category", "misc"),
                    page_id=page_data.get("page_id"),
                    tags=page_data.get("tags"),
                    importance=page_data.get("importance"),
                )
                page_ids.append(pid)

            # 只保存一次索引
            self._save_index()
            for pid in page_ids:
                self._save_page(pid)

            return page_ids

    # ------------------------------------------------------------------------
    # 导入导出
    # ------------------------------------------------------------------------

    def export_pages(self, category: Optional[str] = None) -> List[Dict]:
        """导出页面"""
        with self._lock.read():
            result = []
            for page_id, page in self.pages.items():
                if page is None or page.is_deleted:
                    continue
                if category and page.category != category:
                    continue
                result.append(page.to_dict())
            return result

    def import_pages(self, pages: List[Dict], mode: str = "merge") -> int:
        """导入页面

        Args:
            pages: 页面数据列表
            mode: "merge" 合并(冲突时保留现有), "overwrite" 覆盖
        """
        count = 0
        with self._lock.write():
            for page_data in pages:
                page_id = page_data.get("page_id")

                if mode == "merge" and page_id in self.pages:
                    continue  # 跳过已存在的

                page = MemoryPage.from_dict(page_data)
                self.pages[page_id] = page
                self._update_index(page)
                self._pages_dirty.add(page_id)

                # 更新向量引擎
                if self.enable_vector_search:
                    self.vector_engine.add_document(page_id, page.content)

                count += 1

            self._index_dirty = True

        return count

    # ------------------------------------------------------------------------
    # 事务
    # ------------------------------------------------------------------------

    def transaction(self) -> Transaction:
        """创建事务"""
        return Transaction(self)

    # ------------------------------------------------------------------------
    # 上下文换页
    # ------------------------------------------------------------------------

    def get_working_set(self, query: str, max_pages: int = 10) -> List[Dict]:
        """获取工作集:当前上下文需要的页面"""
        # 使用激活传播获取相关记忆
        if self.enable_activation and self.enable_vector_search:
            return self.activate_memory(query, max_pages)
        else:
            return self.semantic_search(query, max_pages)

    def swap_context(self, new_context: str, max_pages: int = 10) -> List[Dict]:
        """切换上下文"""
        # 清空TLB
        self.tlb.clear()

        # 加载新上下文的工作集
        working_set = self.get_working_set(new_context, max_pages)

        # 预加载到TLB
        for item in working_set:
            page = self._get_page_internal(item["page_id"])
            if page:
                self.tlb.put(item["page_id"], page.to_dict(), page.importance)

        return working_set

    # ------------------------------------------------------------------------
    # 内存管理
    # ------------------------------------------------------------------------

    def _check_memory_limit(self):
        """检查内存限制,必要时换出冷页"""
        if not self.max_memory_mb:
            return

        # 估算内存使用
        estimated_kb = sum(len(p.content.encode('utf-8')) for p in self.pages.values() if p) / 1024

        if estimated_kb > self.max_memory_mb * 1024 * 0.8:
            self._evict_cold_pages()

    def _evict_cold_pages(self, target_ratio: float = 0.3):
        """换出冷页(从内存中真正卸载,但保留索引;仅换出已持久化的非脏页)"""
        if not self.lazy_load:
            return  # 非懒加载模式不支持换出(卸载后无法再从磁盘取回)

        # 候选:未删除、且不在脏集合中(已持久化,可安全从磁盘重载)
        candidates = []
        for pid, page in self.pages.items():
            if page is None or page.is_deleted:
                continue
            if pid in self._pages_dirty:
                continue  # Alpha 8: 绝不换出未保存的脏页
            candidates.append((pid, page.last_accessed, page.access_count))

        if not candidates:
            return

        # 冷页优先:先按最后访问时间,再按访问次数(最老、最少访问的先换出)
        candidates.sort(key=lambda x: (x[1], x[2]))

        evict_count = int(len(candidates) * target_ratio)
        if evict_count <= 0:
            return

        for i in range(evict_count):
            pid = candidates[i][0]
            # 真正从内存卸载:从 self.pages 移除并使 TLB 失效
            self.pages.pop(pid, None)
            self.tlb.invalidate(pid)
            self._stats["page_evictions"] += 1

        # loaded_pages 反映当前驻留内存的页数
        self._stats["loaded_pages"] = len(self.pages)

    # ------------------------------------------------------------------------
    # 访问模式分析
    # ------------------------------------------------------------------------

    def analyze_access_patterns(self) -> Dict:
        """分析访问模式"""
        with self._lock.read():
            pages = []
            for pid, page in self.pages.items():
                if page and not page.is_deleted:
                    pages.append({
                        "page_id": pid,
                        "label": page.label,
                        "category": page.category,
                        "access_count": page.access_count,
                        "last_accessed": page.last_accessed,
                        "importance": page.importance,
                        "memory_strength": page.memory_strength if self.enable_forgetting else None,
                    })

            # 按访问次数排序
            pages.sort(key=lambda x: x["access_count"], reverse=True)

            # 分类统计
            category_stats = defaultdict(lambda: {"count": 0, "total_accesses": 0})
            for p in pages:
                cat = p["category"]
                category_stats[cat]["count"] += 1
                category_stats[cat]["total_accesses"] += p["access_count"]

            # 热点页面(前20%)
            hot_count = max(1, len(pages) // 5)
            hot_pages = pages[:hot_count]

            return {
                "total_pages": len(pages),
                "hot_pages": hot_pages[:10],  # 前10个热点
                "cold_pages": pages[-10:] if len(pages) > 10 else [],  # 后10个冷点
                "category_stats": dict(category_stats),
                "distribution": {
                    "hot_20_percent_accesses": sum(p["access_count"] for p in hot_pages),
                    "total_accesses": sum(p["access_count"] for p in pages),
                },
            }

    # ------------------------------------------------------------------------
    # 保存与关闭
    # ------------------------------------------------------------------------

    def save(self):
        """手动保存所有数据"""
        with self._lock.write():
            self._save_all()

    def close(self):
        """关闭引擎,保存所有数据"""
        self.save()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    """命令行接口"""
    import argparse

    parser = argparse.ArgumentParser(description="OxygenMemo v26.0 Alpha 8 - 高级记忆管理引擎")
    parser.add_argument("--path", default="./oxygen_memo_data", help="存储路径")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--health", action="store_true", help="运行健康检查")
    parser.add_argument("--consistency", action="store_true", help="运行一致性检查")
    parser.add_argument("--consolidate", action="store_true", help="执行记忆巩固")
    parser.add_argument("--gc", action="store_true", help="执行垃圾回收")
    parser.add_argument("--search", help="语义搜索关键词")
    parser.add_argument("--review", action="store_true", help="显示需要复习的页面")
    parser.add_argument("--entities", help="搜索知识图谱实体")
    parser.add_argument("--version", action="store_true", help="显示版本")

    args = parser.parse_args()

    if args.version:
        # 人类可读版本标签: 26.0.0-alpha.8 -> v26.0 Alpha 8
        _v = OxygenMemo.VERSION
        _display = _v
        _m = re.match(r"(\d+)\.(\d+)\.\d+-alpha\.(\d+)", _v)
        if _m:
            _display = f"v{_m.group(1)}.{_m.group(2)} Alpha {_m.group(3)}"
        print(f"OxygenMemo {_display} ({OxygenMemo.VERSION})")
        print("GitHub@StarsailsClover")
        return

    memo = OxygenMemo(storage_path=args.path)

    if args.stats:
        stats = memo.get_stats()
        print(json.dumps(stats, ensure_ascii=False, indent=2))

    if args.health:
        health = memo.health_check()
        print(f"健康评分: {health['score']}/100")
        print(f"总页面数: {health['total_pages']}")
        print(f"内存使用: {health['memory_usage_kb']:.2f} KB")
        if health['suggestions']:
            print("\n建议:")
            for s in health['suggestions']:
                print(f"  - {s}")

    if args.consistency:
        result = memo.check_consistency()
        print(f"一致性检查: 发现 {result['issues_found']} 个问题")
        if result['issues_found'] > 0:
            print(json.dumps(result['details'], ensure_ascii=False, indent=2))

    if args.consolidate:
        stats = memo.consolidate_memory()
        print("记忆巩固完成:")
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        memo.save()

    if args.gc:
        stats = memo.collect_garbage()
        print("垃圾回收完成:")
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        memo.save()

    if args.search:
        results = memo.semantic_search(args.search, top_k=10)
        print(f"搜索结果: 找到 {len(results)} 个相关页面")
        for i, r in enumerate(results, 1):
            print(f"{i}. [{r['score']:.3f}] {r['label']} ({r['category']})")
            print(f"   {r['snippet'][:100]}...")

    if args.review:
        needs = memo.get_pages_needing_review(threshold=0.7, limit=20)
        print(f"需要复习的页面: {len(needs)} 个")
        for i, r in enumerate(needs, 1):
            print(f"{i}. [{r['retention']:.3f}] {r['label']} (强度: {r['strength']})")

    if args.entities:
        results = memo.search_entities(args.entities, top_k=10)
        print(f"找到 {len(results)} 个相关实体")
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['name']} ({r['type']}) - {r['mentions']}次提及")

    memo.close()


if __name__ == "__main__":
    main()
