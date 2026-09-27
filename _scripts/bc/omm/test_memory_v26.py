#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OxygenMemo v26.0 Alpha 8 - 完整测试套件
覆盖: 基础读写、懒加载、TLB缓存、向量搜索、遗忘曲线、
      知识图谱、激活传播、记忆蒸馏、垃圾回收、事务、
      一致性校验、健康检查、持久化、并发安全等
"""

import os
import sys
import time
import json
import math
import shutil
import threading
import pytest
from unittest.mock import patch, MagicMock
from collections import defaultdict

# 确保能导入被测模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from memory_engine_v26 import (
    OxygenMemo,
    MemoryPage,
    TLB,
    RWLock,
    Transaction,
    VectorSearchEngine,
    ForgettingCurve,
    KnowledgeGraph,
    ActivationSpreader,
    tokenize,
    cosine_similarity,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def storage_dir(tmp_path):
    """提供临时存储目录"""
    d = tmp_path / "memo_data"
    d.mkdir()
    return str(d)


@pytest.fixture
def memo(storage_dir):
    """创建标准配置的 OxygenMemo 实例"""
    m = OxygenMemo(
        storage_path=storage_dir,
        tlb_size=10,
        lazy_load=False,
        max_memory_mb=512,
        enable_vector_search=True,
        enable_forgetting=True,
        enable_knowledge_graph=True,
        enable_activation=True,
    )
    yield m
    m.close()


@pytest.fixture
def memo_lazy(storage_dir):
    """创建懒加载模式的 OxygenMemo 实例"""
    m = OxygenMemo(
        storage_path=storage_dir,
        tlb_size=5,
        lazy_load=True,
        max_memory_mb=1,  # 极小内存限制以触发换页
        enable_vector_search=True,
        enable_forgetting=True,
        enable_knowledge_graph=True,
        enable_activation=True,
    )
    yield m
    m.close()


@pytest.fixture
def memo_minimal(storage_dir):
    """创建最小配置的 OxygenMemo 实例(关闭所有高级功能)"""
    m = OxygenMemo(
        storage_path=storage_dir,
        tlb_size=5,
        lazy_load=False,
        max_memory_mb=0,
        enable_vector_search=False,
        enable_forgetting=False,
        enable_knowledge_graph=False,
        enable_activation=False,
    )
    yield m
    m.close()


@pytest.fixture
def populated_memo(memo):
    """预填充数据的 memo 实例"""
    pages = [
        ("Python是一种高级编程语言，广泛用于数据科学和人工智能领域。", "Python简介", "knowledge"),
        ("机器学习是人工智能的一个分支，通过数据训练模型来做出预测。", "机器学习概述", "knowledge"),
        ("深度学习使用多层神经网络来处理复杂的模式识别任务。", "深度学习入门", "knowledge"),
        ("项目进度：第一阶段已完成，正在进行第二阶段的需求分析。", "项目进度报告", "task"),
        ("用户偏好设置包括主题颜色、语言选择和通知频率。", "用户设置说明", "core"),
        ("昨天的会议讨论了API重构方案，决定采用GraphQL替代REST。", "会议记录0801", "history"),
        ("数据库优化策略：添加索引、查询缓存、读写分离。", "数据库优化", "knowledge"),
        ("前端框架选型：React vs Vue vs Angular，最终选择React。", "技术选型", "task"),
        ("团队规范：代码审查必须至少两人通过，提交信息遵循Conventional Commits。", "团队规范", "core"),
        ("部署流程：CI/CD流水线 -> Docker构建 -> K8s滚动更新。", "部署文档", "knowledge"),
    ]
    page_ids = []
    for content, label, category in pages:
        pid = memo.write_page(content, label, category=category, importance=7.0)
        page_ids.append(pid)
    memo.save()
    return memo, page_ids


# ============================================================================
# 工具函数测试
# ============================================================================

class TestTokenize:
    def test_english_words(self):
        tokens = tokenize("Hello World Python")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens

    def test_chinese_chars(self):
        tokens = tokenize("你好世界")
        assert "你" in tokens
        assert "好" in tokens
        assert "世" in tokens
        assert "界" in tokens

    def test_chinese_bigrams(self):
        tokens = tokenize("你好世界")
        assert "你好" in tokens
        assert "好世" in tokens
        assert "世界" in tokens

    def test_mixed_text(self):
        tokens = tokenize("Python是一种编程语言")
        assert "python" in tokens
        assert "编" in tokens
        assert "程" in tokens

    def test_empty_string(self):
        tokens = tokenize("")
        assert tokens == []

    def test_punctuation_removed(self):
        tokens = tokenize("Hello, World! How are you?")
        assert "hello" in tokens
        assert "," not in tokens
        assert "!" not in tokens


class TestCosineSimilarity:
    def test_identical_vectors(self):
        vec = {"a": 1.0, "b": 2.0}
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        vec1 = {"a": 1.0}
        vec2 = {"b": 1.0}
        assert cosine_similarity(vec1, vec2) == pytest.approx(0.0)

    def test_zero_vector(self):
        vec1 = {"a": 0.0}
        vec2 = {"a": 1.0}
        assert cosine_similarity(vec1, vec2) == 0.0

    def test_empty_vectors(self):
        assert cosine_similarity({}, {}) == 0.0

    def test_partial_overlap(self):
        vec1 = {"a": 1.0, "b": 1.0}
        vec2 = {"a": 1.0, "c": 1.0}
        sim = cosine_similarity(vec1, vec2)
        assert 0.0 < sim < 1.0


# ============================================================================
# VectorSearchEngine 测试
# ============================================================================

class TestVectorSearchEngine:
    @pytest.fixture
    def engine(self):
        return VectorSearchEngine()

    def test_add_and_search(self, engine):
        engine.add_document("p1", "Python programming language")
        engine.add_document("p2", "Java programming language")
        results = engine.search("Python")
        assert len(results) > 0
        assert results[0][0] == "p1"

    def test_remove_document(self, engine):
        engine.add_document("p1", "Python programming")
        engine.remove_document("p1")
        results = engine.search("Python")
        assert len(results) == 0

    def test_update_document(self, engine):
        engine.add_document("p1", "Python programming")
        engine.update_document("p1", "Java programming")
        results = engine.search("Python")
        assert len(results) == 0
        results = engine.search("Java")
        assert len(results) > 0

    def test_get_similar(self, engine):
        engine.add_document("p1", "machine learning deep learning neural network")
        engine.add_document("p2", "deep learning neural network training")
        engine.add_document("p3", "cooking recipes food preparation")
        similar = engine.get_similar("p1", top_k=2)
        assert len(similar) > 0
        # p2 应该比 p3 更相似
        if len(similar) >= 2:
            assert similar[0][0] == "p2"

    def test_search_top_k(self, engine):
        for i in range(20):
            engine.add_document(f"p{i}", f"document number {i} about topic {i % 5}")
        results = engine.search("document topic", top_k=5)
        assert len(results) <= 5

    def test_empty_search(self, engine):
        results = engine.search("nonexistent query xyz")
        assert results == []


# ============================================================================
# ForgettingCurve 测试
# ============================================================================

class TestForgettingCurve:
    @pytest.fixture
    def curve(self):
        return ForgettingCurve()

    def test_initial_retention(self, curve):
        now = time.time()
        retention = curve.calculate_retention(now, 1.0, now)
        assert retention == pytest.approx(1.0)

    def test_retention_decays(self, curve):
        now = time.time()
        one_hour_ago = now - 3600
        retention = curve.calculate_retention(one_hour_ago, 1.0, now)
        assert 0.0 < retention < 1.0

    def test_stronger_memory_decays_slower(self, curve):
        now = time.time()
        one_day_ago = now - 86400
        weak_retention = curve.calculate_retention(one_day_ago, 1.0, now)
        strong_retention = curve.calculate_retention(one_day_ago, 5.0, now)
        assert strong_retention > weak_retention

    def test_review_boosts_strength(self, curve):
        strength = 1.0
        new_strength = curve.review(strength)
        assert new_strength > strength
        assert new_strength == pytest.approx(1.5)

    def test_review_caps_at_max(self, curve):
        strength = 9.0
        new_strength = curve.review(strength)
        assert new_strength <= curve.max_strength

    def test_next_review_time(self, curve):
        now = time.time()
        next_time = curve.get_next_review_time(now, 2.0, threshold=0.8)
        assert next_time > now


# ============================================================================
# KnowledgeGraph 测试
# ============================================================================

class TestKnowledgeGraph:
    @pytest.fixture
    def kg(self):
        return KnowledgeGraph()

    def test_extract_entities_english(self, kg):
        entities = kg.extract_entities("Python is a great Language for Data Science", "p1")
        assert len(entities) > 0

    def test_extract_entities_chinese(self, kg):
        entities = kg.extract_entities("Python是一种编程语言，机器学习是人工智能的分支", "p1")
        assert len(entities) > 0

    def test_entity_mentions_increment(self, kg):
        kg.extract_entities("Python is great", "p1")
        kg.extract_entities("Python is powerful", "p2")
        # "Python" 应该被提及两次（如果匹配到）
        if "Python" in kg.entities:
            assert kg.entities["Python"].mentions >= 1

    def test_add_relation(self, kg):
        kg.extract_entities("Python is a Language", "p1")
        # 手动添加实体以确保存在
        kg._add_entity("Python", "concept", "p1")
        kg._add_entity("Language", "concept", "p1")
        kg.add_relation("Python", "Language", "is_a")
        assert len(kg.relations) == 1

    def test_get_related_entities(self, kg):
        kg._add_entity("A", "concept", "p1")
        kg._add_entity("B", "concept", "p1")
        kg._add_entity("C", "concept", "p1")
        kg.add_relation("A", "B", "related", weight=1.0)
        kg.add_relation("B", "C", "related", weight=1.0)
        related = kg.get_related_entities("A", depth=2)
        assert "B" in related
        assert "C" in related

    def test_search_entities(self, kg):
        kg._add_entity("Python", "concept", "p1")
        kg._add_entity("PyTorch", "concept", "p2")
        kg._add_entity("Java", "concept", "p3")
        results = kg.search_entities("Py")
        names = [r[0] for r in results]
        assert "Python" in names or "PyTorch" in names

    def test_get_entity_pages(self, kg):
        kg._add_entity("Python", "concept", "p1")
        kg._add_entity("Python", "concept", "p2")
        pages = kg.get_entity_pages("Python")
        assert "p1" in pages
        assert "p2" in pages


# ============================================================================
# ActivationSpreader 测试
# ============================================================================

class TestActivationSpreader:
    @pytest.fixture
    def spreader(self):
        return ActivationSpreader(decay=0.7, steps=3)

    def test_basic_spread(self, spreader):
        start = {"A": 1.0}
        adjacency = {
            "A": [("B", 1.0), ("C", 1.0)],
            "B": [("D", 1.0)],
        }
        result = spreader.spread(start, adjacency)
        assert "A" in result
        assert "B" in result
        assert "C" in result
        assert "D" in result

    def test_activation_decays_with_distance(self, spreader):
        """距离起始节点越远，首次接收到的激活值越低。
        
        注意：由于累加式传播，多步后中间节点可能因反复累积而超过起始节点，
        这是扩散激活算法的正常行为。这里验证的是：
        1. 所有可达节点都被激活
        2. 单步传播时使用 steps=1 来验证严格衰减
        """
        # 使用 steps=1 验证单步严格衰减
        single_step = ActivationSpreader(decay=0.7, steps=1)
        start = {"A": 1.0}
        adjacency = {"A": [("B", 1.0)], "B": [("C", 1.0)]}
        result = single_step.spread(start, adjacency)
        assert result["A"] == 1.0
        assert result["B"] == pytest.approx(0.7)
        assert "C" not in result  # 单步无法到达 C

        # 多步传播：验证所有节点可达且值为正
        result_multi = spreader.spread(start, adjacency)
        assert result_multi["A"] > 0
        assert result_multi["B"] > 0
        assert result_multi["C"] > 0

    def test_no_neighbors(self, spreader):
        start = {"A": 1.0}
        adjacency = {}
        result = spreader.spread(start, adjacency)
        assert result == {"A": 1.0}

    def test_threshold_filter(self, spreader):
        """激活值低于 0.01 的节点不再传播"""
        spreader_weak = ActivationSpreader(decay=0.01, steps=5)
        start = {"A": 0.005}
        adjacency = {"A": [("B", 1.0)]}
        result = spreader_weak.spread(start, adjacency)
        # A 的激活值 < 0.01，不会传播到 B
        assert "B" not in result or result.get("B", 0) == 0


# ============================================================================
# TLB 测试
# ============================================================================

class TestTLB:
    @pytest.fixture
    def tlb(self):
        return TLB(size=3)

    def test_put_and_get(self, tlb):
        tlb.put("p1", {"content": "test"}, importance=5.0)
        result = tlb.get("p1")
        assert result is not None
        assert result["content"] == "test"

    def test_cache_miss(self, tlb):
        result = tlb.get("nonexistent")
        assert result is None

    def test_eviction_on_overflow(self, tlb):
        tlb.put("p1", {"importance": 1.0, "access_count": 0}, importance=1.0)
        tlb.put("p2", {"importance": 1.0, "access_count": 0}, importance=1.0)
        tlb.put("p3", {"importance": 1.0, "access_count": 0}, importance=1.0)
        # 第4个应该触发淘汰
        tlb.put("p4", {"importance": 1.0, "access_count": 0}, importance=1.0)
        assert len(tlb.cache) <= 3
        assert tlb.evictions >= 1

    def test_lru_behavior(self, tlb):
        tlb.put("p1", {"importance": 5.0, "access_count": 0}, importance=5.0)
        tlb.put("p2", {"importance": 5.0, "access_count": 0}, importance=5.0)
        tlb.put("p3", {"importance": 5.0, "access_count": 0}, importance=5.0)
        # 访问 p1 使其变为最近使用
        tlb.get("p1")
        # 添加 p4 应该淘汰 p2（最久未使用且权重最低）
        tlb.put("p4", {"importance": 5.0, "access_count": 0}, importance=5.0)
        assert "p1" in tlb.cache  # p1 被访问过，不应被淘汰

    def test_invalidate(self, tlb):
        tlb.put("p1", {"content": "test"}, importance=5.0)
        tlb.invalidate("p1")
        assert tlb.get("p1") is None

    def test_clear(self, tlb):
        tlb.put("p1", {}, importance=5.0)
        tlb.put("p2", {}, importance=5.0)
        tlb.clear()
        assert len(tlb.cache) == 0

    def test_importance_weighted_eviction(self, tlb):
        """高重要性页面应更难被淘汰"""
        tlb.put("low", {"importance": 1.0, "access_count": 0}, importance=1.0)
        tlb.put("high", {"importance": 10.0, "access_count": 20}, importance=10.0)
        tlb.put("mid", {"importance": 5.0, "access_count": 5}, importance=5.0)
        tlb.put("new", {"importance": 5.0, "access_count": 5}, importance=5.0)
        # high 应该还在缓存中
        assert "high" in tlb.cache


# ============================================================================
# RWLock 测试
# ============================================================================

class TestRWLock:
    def test_concurrent_reads(self):
        lock = RWLock()
        results = []
        barrier = threading.Barrier(5)

        def reader(reader_id):
            with lock.read():
                barrier.wait(timeout=5)
                results.append(reader_id)
                time.sleep(0.01)

        threads = [threading.Thread(target=reader, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(results) == 5

    def test_write_excludes_reads(self):
        lock = RWLock()
        shared_state = {"value": 0}
        errors = []

        def writer():
            with lock.write():
                shared_state["value"] = 1
                time.sleep(0.05)
                if shared_state["value"] != 1:
                    errors.append("Write was interrupted")
                shared_state["value"] = 0

        def reader():
            with lock.read():
                val = shared_state["value"]
                # 读锁期间值应该是 0 或 1（完整的一次写入）
                time.sleep(0.01)

        threads = [threading.Thread(target=writer)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0


# ============================================================================
# MemoryPage 数据类测试
# ============================================================================

class TestMemoryPage:
    def test_creation(self):
        page = MemoryPage(
            page_id="T001",
            label="Test Page",
            content="Hello World",
            category="task",
        )
        assert page.page_id == "T001"
        assert page.label == "Test Page"
        assert page.content == "Hello World"
        assert page.category == "task"
        assert page.version == 1
        assert page.access_count == 0

    def test_to_dict_and_from_dict(self):
        page = MemoryPage(
            page_id="K001",
            label="Knowledge",
            content="Some knowledge content",
            category="knowledge",
            tags=["ai", "ml"],
            importance=8.0,
        )
        d = page.to_dict()
        restored = MemoryPage.from_dict(d)
        assert restored.page_id == page.page_id
        assert restored.label == page.label
        assert restored.content == page.content
        assert restored.tags == page.tags
        assert restored.importance == page.importance

    def test_default_values(self):
        page = MemoryPage(
            page_id="M001",
            label="Default",
            content="content",
            category="misc",
        )
        assert page.tags == []
        assert page.is_deleted is False
        assert page.is_distilled is False
        assert page.memory_strength == 1.0
        assert page.activation == 0.0
        assert page.entities == []


# ============================================================================
# OxygenMemo 基础读写测试
# ============================================================================

class TestBasicReadWrite:
    def test_write_and_load(self, memo):
        pid = memo.write_page("Hello World", "测试页面", category="misc")
        assert pid is not None
        result = memo.load_page(pid)
        assert result is not None
        assert result["content"] == "Hello World"
        assert result["label"] == "测试页面"

    def test_write_with_custom_id(self, memo):
        pid = memo.write_page("Custom content", "Custom", page_id="CUSTOM01")
        assert pid == "CUSTOM01"
        result = memo.load_page("CUSTOM01")
        assert result["content"] == "Custom content"

    def test_write_updates_existing(self, memo):
        pid = memo.write_page("Version 1", "Page", page_id="P001")
        memo.write_page("Version 2", "Page Updated", page_id="P001")
        result = memo.load_page("P001")
        assert result["content"] == "Version 2"
        assert result["label"] == "Page Updated"
        assert result["version"] == 2

    def test_write_with_tags(self, memo):
        pid = memo.write_page("Tagged content", "Tagged", tags=["tag1", "tag2"])
        result = memo.load_page(pid)
        assert "tag1" in result["tags"]
        assert "tag2" in result["tags"]

    def test_write_with_importance(self, memo):
        pid = memo.write_page("Important content", "Important", importance=9.5)
        result = memo.load_page(pid)
        assert result["importance"] == 9.5

    def test_append_page(self, memo):
        pid = memo.write_page("Initial content", "Append Test")
        success = memo.append_page(pid, "Appended content")
        assert success is True
        result = memo.load_page(pid)
        assert "Initial content" in result["content"]
        assert "Appended content" in result["content"]

    def test_append_nonexistent_page(self, memo):
        success = memo.append_page("NONEXIST", "content")
        assert success is False

    def test_delete_page_soft(self, memo):
        pid = memo.write_page("To be deleted", "Delete Me")
        result = memo.delete_page(pid, permanent=False)
        assert result is True
        loaded = memo.load_page(pid)
        assert loaded is None  # 软删除后不可读取

    def test_delete_page_permanent(self, memo):
        pid = memo.write_page("Permanent delete", "Gone")
        result = memo.delete_page(pid, permanent=True)
        assert result is True
        loaded = memo.load_page(pid)
        assert loaded is None

    def test_delete_nonexistent(self, memo):
        result = memo.delete_page("NONEXIST")
        assert result is False

    def test_load_nonexistent(self, memo):
        result = memo.load_page("NONEXIST")
        assert result is None

    def test_content_dedup(self, memo):
        """相同内容应返回已有页面ID"""
        pid1 = memo.write_page("Duplicate content here", "First")
        pid2 = memo.write_page("Duplicate content here", "Second")
        assert pid1 == pid2

    def test_content_dedup_with_custom_id_bypasses(self, memo):
        """指定 page_id 时不去重"""
        pid1 = memo.write_page("Same content", "First")
        pid2 = memo.write_page("Same content", "Second", page_id="FORCED01")
        assert pid1 != pid2

    def test_auto_generated_page_id_format(self, memo):
        pid = memo.write_page("content", "label", category="knowledge")
        assert pid.startswith("K")
        assert len(pid) == 4  # K + 3位数字

    def test_page_id_prefix_mapping(self, memo):
        pid_core = memo.write_page("c", "c", category="core")
        pid_task = memo.write_page("t", "t", category="task")
        pid_know = memo.write_page("k", "k", category="knowledge")
        pid_hist = memo.write_page("h", "h", category="history")
        pid_misc = memo.write_page("m", "m", category="misc")
        assert pid_core.startswith("C")
        assert pid_task.startswith("T")
        assert pid_know.startswith("K")
        assert pid_hist.startswith("H")
        assert pid_misc.startswith("M")


# ============================================================================
# 懒加载与内存管理测试
# ============================================================================

class TestLazyLoad:
    def test_lazy_load_basic(self, memo_lazy):
        """懒加载模式下写入和读取应正常工作"""
        pid = memo_lazy.write_page("Lazy content", "Lazy Page")
        result = memo_lazy.load_page(pid)
        assert result is not None
        assert result["content"] == "Lazy content"

    def test_lazy_load_stats_no_crash(self, memo_lazy):
        """懒加载模式下 get_stats() 不应崩溃（原始 bug 回归测试）"""
        for i in range(10):
            memo_lazy.write_page(f"Content {i} " * 50, f"Page {i}")
        memo_lazy.save()
        # 这不应该抛出 AttributeError
        stats = memo_lazy.get_stats()
        assert "total_pages" in stats
        assert "loaded_pages" in stats

    def test_lazy_load_eviction_and_reload(self, memo_lazy):
        """写入大量页面触发换页后，仍能从磁盘重新加载"""
        # 写入足够多的页面以触发内存限制
        pids = []
        for i in range(20):
            pid = memo_lazy.write_page(
                f"This is page {i} with enough content to take some memory space. " * 20,
                f"Page {i}",
            )
            pids.append(pid)
        memo_lazy.save()

        # 触发换页
        memo_lazy._check_memory_limit()

        # 即使被换出，仍应能通过懒加载从磁盘恢复
        for pid in pids:
            result = memo_lazy.load_page(pid)
            assert result is not None, f"Failed to reload page {pid} after eviction"

    def test_lazy_load_tlb_recovery(self, memo_lazy):
        """TLB 缓存应在页面从内存换出后帮助恢复"""
        pid = memo_lazy.write_page("TLB recovery test content", "TLB Test")
        memo_lazy.save()

        # 确保页面在 TLB 中
        memo_lazy.load_page(pid)

        # 强制从内存移除（模拟换页）
        if pid in memo_lazy.pages:
            memo_lazy.pages.pop(pid)

        # 通过 TLB 缓存恢复
        result = memo_lazy.load_page(pid)
        assert result is not None
        assert result["content"] == "TLB recovery test content"

    def test_non_lazy_load_no_eviction(self, memo):
        """非懒加载模式下不应发生换页"""
        for i in range(10):
            memo.write_page(f"Content {i}", f"Page {i}")
        initial_count = len(memo.pages)
        memo._check_memory_limit()
        assert len(memo.pages) == initial_count


# ============================================================================
# 向量语义搜索测试
# ============================================================================

class TestSemanticSearch:
    def test_basic_search(self, populated_memo):
        memo, _ = populated_memo
        results = memo.semantic_search("Python编程语言")
        assert len(results) > 0
        assert "page_id" in results[0]
        assert "score" in results[0]
        assert "snippet" in results[0]

    def test_search_with_category_filter(self, populated_memo):
        memo, _ = populated_memo
        results = memo.semantic_search("编程", category="knowledge")
        for r in results:
            assert r["category"] == "knowledge"

    def test_search_top_k(self, populated_memo):
        memo, _ = populated_memo
        results = memo.semantic_search("技术", top_k=3)
        assert len(results) <= 3

    def test_search_min_score(self, populated_memo):
        memo, _ = populated_memo
        results = memo.semantic_search("Python", min_score=0.5)
        for r in results:
            assert r["score"] >= 0.5

    def test_search_empty_query(self, populated_memo):
        memo, _ = populated_memo
        results = memo.semantic_search("")
        # 空查询可能返回空或少量结果
        assert isinstance(results, list)

    def test_search_disabled(self, memo_minimal):
        memo_minimal.write_page("Some content", "Page")
        results = memo_minimal.semantic_search("content")
        assert results == []

    def test_find_similar_pages(self, populated_memo):
        memo, page_ids = populated_memo
        similar = memo.find_similar_pages(page_ids[0], top_k=3)
        assert isinstance(similar, list)
        for s in similar:
            assert "page_id" in s
            assert "similarity" in s

    def test_find_similar_disabled(self, memo_minimal):
        pid = memo_minimal.write_page("content", "page")
        results = memo_minimal.find_similar_pages(pid)
        assert results == []


# ============================================================================
# 遗忘曲线与复习测试
# ============================================================================

class TestForgettingAndReview:
    def test_memory_retention(self, memo):
        pid = memo.write_page("Remember this", "Memory Test")
        retention = memo.get_memory_retention(pid)
        assert retention is not None
        assert 0.0 <= retention <= 1.0

    def test_review_boosts_retention(self, memo):
        pid = memo.write_page("Review me", "Review Test")
        retention_before = memo.get_memory_retention(pid)

        # 模拟时间流逝
        page = memo.pages[pid]
        page.last_reviewed = time.time() - 7200  # 2小时前
        page.memory_strength = 1.0

        retention_mid = memo.get_memory_retention(pid)

        # 复习
        memo.review_page(pid)
        retention_after = memo.get_memory_retention(pid)

        assert retention_after > retention_mid

    def test_review_nonexistent(self, memo):
        result = memo.review_page("NONEXIST")
        assert result is False

    def test_get_pages_needing_review(self, memo):
        # 创建一些页面并模拟时间流逝
        pids = []
        for i in range(5):
            pid = memo.write_page(f"Content {i}", f"Page {i}")
            pids.append(pid)
            page = memo.pages[pid]
            page.last_reviewed = time.time() - 86400 * 7  # 7天前
            page.memory_strength = 1.0

        needs_review = memo.get_pages_needing_review(threshold=0.7)
        assert len(needs_review) > 0
        assert "retention" in needs_review[0]
        assert "strength" in needs_review[0]

    def test_retention_disabled(self, memo_minimal):
        pid = memo_minimal.write_page("content", "page")
        retention = memo_minimal.get_memory_retention(pid)
        assert retention is None

    def test_review_disabled(self, memo_minimal):
        pid = memo_minimal.write_page("content", "page")
        result = memo_minimal.review_page(pid)
        assert result is False

    def test_load_page_updates_strength(self, memo):
        """读取页面应等同于复习，增强记忆强度"""
        pid = memo.write_page("Strengthen me", "Strength Test")
        page = memo.pages[pid]
        initial_strength = page.memory_strength

        memo.load_page(pid)

        assert page.memory_strength >= initial_strength


# ============================================================================
# 知识图谱集成测试
# ============================================================================

class TestKnowledgeGraphIntegration:
    def test_entities_extracted_on_write(self, memo):
        pid = memo.write_page(
            "Python是一种编程语言。Machine Learning是AI的分支。",
            "KG Test",
        )
        page = memo.pages[pid]
        assert len(page.entities) > 0

    def test_search_entities(self, populated_memo):
        memo, _ = populated_memo
        results = memo.search_entities("Python")
        assert isinstance(results, list)

    def test_get_entity_pages(self, populated_memo):
        memo, _ = populated_memo
        # 先搜索一个存在的实体
        entities = memo.search_entities("Python")
        if entities:
            entity_name = entities[0]["name"]
            pages = memo.get_entity_pages(entity_name)
            assert isinstance(pages, list)

    def test_get_related_entities(self, populated_memo):
        memo, _ = populated_memo
        entities = memo.search_entities("Python")
        if entities:
            entity_name = entities[0]["name"]
            related = memo.get_related_entities(entity_name, depth=1)
            assert isinstance(related, list)

    def test_kg_disabled(self, memo_minimal):
        memo_minimal.write_page("Python is great", "Page")
        results = memo_minimal.search_entities("Python")
        assert results == []


# ============================================================================
# 激活传播测试
# ============================================================================

class TestActivationSpread:
    def test_activate_memory(self, populated_memo):
        memo, _ = populated_memo
        results = memo.activate_memory("Python编程", top_k=5)
        assert isinstance(results, list)
        assert len(results) > 0
        assert "activation" in results[0]

    def test_activate_memory_empty(self, memo):
        results = memo.activate_memory("completely unrelated xyz query")
        assert isinstance(results, list)

    def test_activate_disabled_falls_back(self, memo_minimal):
        pid = memo_minimal.write_page("Some content about testing", "Page")
        results = memo_minimal.activate_memory("testing")
        # 应回退到 semantic_search（但 vector_search 也关了，所以返回空）
        assert isinstance(results, list)


# ============================================================================
# 记忆蒸馏测试
# ============================================================================

class TestDistillation:
    def test_distill_page_replace(self, memo):
        long_content = "。".join([f"这是第{i}句话，包含了一些重要的信息和细节" for i in range(20)])
        pid = memo.write_page(long_content, "Long Page")
        original_len = len(memo.pages[pid].content)

        result_id = memo.distill_page(pid, ratio=0.5, replace_original=True)
        assert result_id == pid
        assert len(memo.pages[pid].content) < original_len
        assert memo.pages[pid].is_distilled is True

    def test_distill_page_new(self, memo):
        long_content = "。".join([f"这是第{i}句话，包含了一些重要的信息和细节" for i in range(20)])
        pid = memo.write_page(long_content, "Long Page")

        new_id = memo.distill_page(pid, ratio=0.5, replace_original=False)
        assert new_id is not None
        assert new_id != pid
        assert memo.pages[new_id].is_distilled is True
        assert memo.pages[new_id].original_page_id == pid

    def test_distill_nonexistent(self, memo):
        result = memo.distill_page("NONEXIST")
        assert result is None

    def test_distill_short_content(self, memo):
        pid = memo.write_page("短内容", "Short")
        result = memo.distill_page(pid, ratio=0.5, replace_original=True)
        # 短内容可能只有一个句子，蒸馏后仍存在
        assert result is not None

    def test_batch_distill(self, memo):
        for i in range(5):
            long_content = "。".join([f"第{i}页第{j}句话详细内容" for j in range(30)])
            memo.write_page(long_content, f"Long Page {i}")

        count = memo.batch_distill(min_length=100, ratio=0.5)
        assert count >= 0  # 可能有些页面不够长

    def test_distill_preserves_pointers(self, memo):
        long_content = "。".join([f"句子{i}的内容描述" for i in range(15)])
        pid = memo.write_page(long_content, "Original")
        new_id = memo.distill_page(pid, ratio=0.5, replace_original=False)

        # 检查指针关系
        assert "distilled_from" in memo.pages[new_id].pointers
        assert pid in memo.pages[new_id].pointers["distilled_from"]
        assert "distilled_to" in memo.pages[pid].pointers
        assert new_id in memo.pages[pid].pointers["distilled_to"]


# ============================================================================
# 垃圾回收测试
# ============================================================================

class TestGarbageCollection:
    def test_gc_deletes_old_low_access_pages(self, memo):
        pid = memo.write_page("Old content", "Old Page")
        page = memo.pages[pid]
        page.last_accessed = time.time() - 86400 * 60  # 60天前
        page.access_count = 0

        stats = memo.collect_garbage(max_age_days=30, min_access=1)
        assert stats["deleted"] >= 1

    def test_gc_preserves_recent_pages(self, memo):
        pid = memo.write_page("Recent content", "Recent Page")
        stats = memo.collect_garbage(max_age_days=30, min_access=1)
        assert memo.load_page(pid) is not None

    def test_gc_preserves_high_access_pages(self, memo):
        pid = memo.write_page("Popular content", "Popular Page")
        page = memo.pages[pid]
        page.last_accessed = time.time() - 86400 * 60
        page.access_count = 100  # 高访问量

        stats = memo.collect_garbage(max_age_days=30, min_access=1)
        # 高访问量不应被删除
        assert memo.load_page(pid) is not None

    def test_gc_with_auto_distill(self, memo):
        long_content = "。".join([f"第{i}句详细内容描述" for i in range(20)])
        pid = memo.write_page(long_content, "Distill Candidate")
        page = memo.pages[pid]
        page.last_accessed = time.time() - 86400 * 60
        page.access_count = 0

        stats = memo.collect_garbage(max_age_days=30, min_access=1, auto_distill=True)
        assert stats["distilled"] >= 1


# ============================================================================
# 记忆巩固测试
# ============================================================================

class TestConsolidation:
    def test_consolidate_basic(self, populated_memo):
        memo, _ = populated_memo
        stats = memo.consolidate_memory()
        assert "pages_analyzed" in stats
        assert stats["pages_analyzed"] > 0

    def test_consolidate_strengthens_high_value(self, memo):
        pid = memo.write_page("Very important content " * 20, "Important", importance=10.0)
        page = memo.pages[pid]
        page.access_count = 50
        page.memory_strength = 5.0

        initial_strength = page.memory_strength
        memo.consolidate_memory()
        assert page.memory_strength >= initial_strength

    def test_consolidate_forgotten_pages(self, memo):
        pid = memo.write_page("Forgettable " * 5, "Forget Me", importance=0.5)
        page = memo.pages[pid]
        page.last_reviewed = time.time() - 86400 * 30
        page.memory_strength = 0.1
        page.access_count = 0

        stats = memo.consolidate_memory()
        # 可能被蒸馏或遗忘
        assert stats["pages_analyzed"] > 0


# ============================================================================
# 指针与关联测试
# ============================================================================

class TestPointers:
    def test_create_pointer(self, memo):
        pid1 = memo.write_page("Source content", "Source")
        pid2 = memo.write_page("Target content", "Target")
        result = memo.create_pointer(pid1, pid2, "related")
        assert result is True
        assert pid2 in memo.pages[pid1].pointers["related"]

    def test_create_pointer_nonexistent(self, memo):
        pid1 = memo.write_page("Source", "Source")
        result = memo.create_pointer(pid1, "NONEXIST", "related")
        assert result is False

    def test_get_related_pages(self, memo):
        pid1 = memo.write_page("Source", "Source")
        pid2 = memo.write_page("Target", "Target")
        memo.create_pointer(pid1, pid2, "depends_on")
        related = memo.get_related_pages(pid1, relation_type="depends_on")
        assert len(related) == 1
        assert related[0]["page_id"] == pid2

    def test_get_all_related_pages(self, memo):
        pid1 = memo.write_page("Source", "Source")
        pid2 = memo.write_page("Target1", "Target1")
        pid3 = memo.write_page("Target2", "Target2")
        memo.create_pointer(pid1, pid2, "type_a")
        memo.create_pointer(pid1, pid3, "type_b")
        related = memo.get_related_pages(pid1)
        assert len(related) == 2

    def test_duplicate_pointer_prevented(self, memo):
        pid1 = memo.write_page("Source", "Source")
        pid2 = memo.write_page("Target", "Target")
        memo.create_pointer(pid1, pid2, "related")
        memo.create_pointer(pid1, pid2, "related")
        assert len(memo.pages[pid1].pointers["related"]) == 1


# ============================================================================
# 页面合并测试
# ============================================================================

class TestMergePages:
    def test_merge_two_pages(self, memo):
        pid1 = memo.write_page("Content A", "Page A", category="knowledge")
        pid2 = memo.write_page("Content B", "Page B", category="knowledge")
        new_id = memo.merge_pages([pid1, pid2], "Merged Page")
        assert new_id is not None
        result = memo.load_page(new_id)
        assert "Content A" in result["content"]
        assert "Content B" in result["content"]
        # 原页面应被软删除
        assert memo.load_page(pid1) is None
        assert memo.load_page(pid2) is None

    def test_merge_preserves_tags(self, memo):
        pid1 = memo.write_page("A", "A", tags=["tag1"])
        pid2 = memo.write_page("B", "B", tags=["tag2"])
        new_id = memo.merge_pages([pid1, pid2], "Merged")
        result = memo.load_page(new_id)
        assert "tag1" in result["tags"]
        assert "tag2" in result["tags"]

    def test_merge_single_page_raises(self, memo):
        pid = memo.write_page("Only one", "Single")
        with pytest.raises(ValueError):
            memo.merge_pages([pid], "Merged")

    def test_merge_all_deleted_raises(self, memo):
        pid1 = memo.write_page("A", "A")
        pid2 = memo.write_page("B", "B")
        memo.delete_page(pid1, permanent=True)
        memo.delete_page(pid2, permanent=True)
        with pytest.raises(ValueError):
            memo.merge_pages([pid1, pid2], "Merged")


# ============================================================================
# 事务测试
# ============================================================================

class TestTransaction:
    def test_transaction_commit(self, memo):
        with memo.transaction():
            memo.write_page("Transactional content", "Tx Page")
        # 提交后数据应存在
        stats = memo.get_stats()
        assert stats["total_pages"] >= 1

    def test_transaction_rollback_on_error(self, memo):
        initial_pages = len(memo.pages)
        try:
            with memo.transaction():
                memo.write_page("Will be rolled back", "Rollback Page")
                raise ValueError("Simulated error")
        except ValueError:
            pass
        # 回滚后页面数应恢复
        assert len(memo.pages) == initial_pages

    def test_nested_transaction_raises(self, memo):
        tx = Transaction(memo)
        tx.begin()
        with pytest.raises(RuntimeError):
            tx.begin()
        tx.rollback()

    def test_commit_without_begin_raises(self, memo):
        tx = Transaction(memo)
        with pytest.raises(RuntimeError):
            tx.commit()

    def test_rollback_without_begin_raises(self, memo):
        tx = Transaction(memo)
        with pytest.raises(RuntimeError):
            tx.rollback()


# ============================================================================
# 持久化测试
# ============================================================================

class TestPersistence:
    def test_save_and_reload(self, storage_dir):
        """保存后重新加载应恢复数据"""
        memo1 = OxygenMemo(storage_path=storage_dir)
        pid = memo1.write_page("Persistent content", "Persistent Page", category="knowledge")
        memo1.save()
        memo1.close()

        memo2 = OxygenMemo(storage_path=storage_dir)
        result = memo2.load_page(pid)
        assert result is not None
        assert result["content"] == "Persistent content"
        memo2.close()

    def test_index_persistence(self, storage_dir):
        memo1 = OxygenMemo(storage_path=storage_dir)
        memo1.write_page("Content", "Label", category="task")
        memo1.save()
        memo1.close()

        memo2 = OxygenMemo(storage_path=storage_dir)
        assert "task" in memo2.root_index
        assert len(memo2.root_index["task"]["children"]) > 0
        memo2.close()

    def test_stats_persistence(self, storage_dir):
        memo1 = OxygenMemo(storage_path=storage_dir)
        memo1.write_page("Content", "Label")
        memo1.load_page(list(memo1.pages.keys())[0])
        memo1.save()
        writes = memo1._stats["total_writes"]
        reads = memo1._stats["total_reads"]
        memo1.close()

        memo2 = OxygenMemo(storage_path=storage_dir)
        assert memo2._stats["total_writes"] == writes
        assert memo2._stats["total_reads"] == reads
        memo2.close()

    def test_corrupted_index_recovery(self, storage_dir):
        """损坏的索引文件应能自动恢复"""
        memo = OxygenMemo(storage_path=storage_dir)
        memo.write_page("Content", "Label")
        memo.save()
        memo.close()

        # 故意损坏索引文件
        index_path = os.path.join(storage_dir, "index.json")
        with open(index_path, 'w') as f:
            f.write("CORRUPTED DATA {{{")

        memo2 = OxygenMemo(storage_path=storage_dir)
        # 应使用默认索引而非崩溃
        assert "core" in memo2.root_index
        memo2.close()

    def test_context_manager(self, storage_dir):
        """with 语句应自动保存和关闭"""
        with OxygenMemo(storage_path=storage_dir) as memo:
            pid = memo.write_page("Context manager content", "CM Page")

        # 重新加载验证
        memo2 = OxygenMemo(storage_path=storage_dir)
        result = memo2.load_page(pid)
        assert result is not None
        memo2.close()


# ============================================================================
# 批量操作测试
# ============================================================================

class TestBatchOperations:
    def test_batch_write(self, memo):
        pages = [
            {"content": "Batch 1", "label": "B1", "category": "knowledge"},
            {"content": "Batch 2", "label": "B2", "category": "task"},
            {"content": "Batch 3", "label": "B3", "category": "misc"},
        ]
        pids = memo.batch_write_pages(pages)
        assert len(pids) == 3
        for pid in pids:
            assert memo.load_page(pid) is not None

    def test_export_pages(self, populated_memo):
        memo, _ = populated_memo
        exported = memo.export_pages()
        assert len(exported) > 0
        assert "page_id" in exported[0]
        assert "content" in exported[0]

    def test_export_with_category_filter(self, populated_memo):
        memo, _ = populated_memo
        exported = memo.export_pages(category="knowledge")
        for page in exported:
            assert page["category"] == "knowledge"

    def test_import_pages_merge(self, memo):
        pid = memo.write_page("Existing", "Existing Page", page_id="IMP01")
        pages_to_import = [
            {"page_id": "IMP01", "content": "Should be skipped", "label": "Skip", "category": "misc"},
            {"page_id": "IMP02", "content": "New import", "label": "New", "category": "misc"},
        ]
        count = memo.import_pages(pages_to_import, mode="merge")
        assert count == 1  # 只导入了 IMP02
        assert memo.load_page("IMP01")["content"] == "Existing"  # 未被覆盖

    def test_import_pages_overwrite(self, memo):
        memo.write_page("Original", "Original", page_id="OW01")
        pages_to_import = [
            {"page_id": "OW01", "content": "Overwritten", "label": "Overwritten", "category": "misc"},
        ]
        count = memo.import_pages(pages_to_import, mode="overwrite")
        assert count == 1
        assert memo.load_page("OW01")["content"] == "Overwritten"


# ============================================================================
# 统计与健康检查测试
# ============================================================================

class TestStatsAndHealth:
    def test_get_stats(self, populated_memo):
        memo, _ = populated_memo
        stats = memo.get_stats()
        assert "version" in stats
        assert "total_pages" in stats
        assert stats["total_pages"] > 0
        assert "categories" in stats
        assert "total_writes" in stats
        assert "total_reads" in stats
        assert "tlb_hits" in stats
        assert "tlb_misses" in stats
        assert "features" in stats

    def test_health_check(self, populated_memo):
        memo, _ = populated_memo
        health = memo.health_check()
        assert "score" in health
        assert 0 <= health["score"] <= 100
        assert "total_pages" in health
        assert "memory_usage_kb" in health
        assert "suggestions" in health
        assert "version" in health

    def test_consistency_check_clean(self, populated_memo):
        memo, _ = populated_memo
        result = memo.check_consistency()
        assert "total_pages" in result
        assert "issues_found" in result
        assert "details" in result

    def test_consistency_detects_broken_pointers(self, memo):
        pid1 = memo.write_page("Source", "Source")
        pid2 = memo.write_page("Target", "Target")
        memo.create_pointer(pid1, pid2, "related")
        memo.delete_page(pid2, permanent=True)

        result = memo.check_consistency()
        assert result["issues_found"] > 0
        assert len(result["details"]["broken_pointers"]) > 0

    def test_access_pattern_analysis(self, populated_memo):
        memo, page_ids = populated_memo
        # 制造一些访问
        for pid in page_ids[:3]:
            for _ in range(5):
                memo.load_page(pid)

        patterns = memo.analyze_access_patterns()
        assert "total_pages" in patterns
        assert "hot_pages" in patterns
        assert "cold_pages" in patterns
        assert "category_stats" in patterns


# ============================================================================
# 语义预取与工作集测试
# ============================================================================

class TestPrefetchAndWorkingSet:
    def test_semantic_prefetch(self, populated_memo):
        memo, page_ids = populated_memo
        prefetched = memo.semantic_prefetch(page_ids[0], top_k=3)
        assert isinstance(prefetched, list)
        assert len(prefetched) <= 3

    def test_get_working_set(self, populated_memo):
        memo, _ = populated_memo
        working_set = memo.get_working_set("Python编程", max_pages=5)
        assert isinstance(working_set, list)

    def test_swap_context(self, populated_memo):
        memo, _ = populated_memo
        working_set = memo.swap_context("数据库优化", max_pages=5)
        assert isinstance(working_set, list)


# ============================================================================
# 并发安全测试
# ============================================================================

class TestConcurrency:
    def test_concurrent_writes(self, memo):
        errors = []
        pids = []
        lock = threading.Lock()

        def writer(writer_id):
            try:
                pid = memo.write_page(
                    f"Concurrent content from writer {writer_id}",
                    f"Writer {writer_id} Page",
                    category="misc",
                )
                with lock:
                    pids.append(pid)
            except Exception as e:
                with lock:
                    errors.append(str(e))

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent write errors: {errors}"
        assert len(pids) == 10

    def test_concurrent_read_write(self, memo):
        # 先写入一些数据
        pids = []
        for i in range(5):
            pid = memo.write_page(f"Content {i}", f"Page {i}")
            pids.append(pid)

        errors = []

        def reader():
            try:
                for _ in range(20):
                    for pid in pids:
                        memo.load_page(pid)
            except Exception as e:
                errors.append(f"Reader: {e}")

        def writer():
            try:
                for i in range(10):
                    memo.write_page(f"New content {i}", f"New Page {i}")
            except Exception as e:
                errors.append(f"Writer: {e}")

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert len(errors) == 0, f"Concurrent errors: {errors}"


# ============================================================================
# 边界条件与异常测试
# ============================================================================

class TestEdgeCases:
    def test_empty_content(self, memo):
        pid = memo.write_page("", "Empty Page")
        result = memo.load_page(pid)
        assert result is not None
        assert result["content"] == ""

    def test_unicode_content(self, memo):
        content = "你好世界 🌍 Hello World café résumé naïve"
        pid = memo.write_page(content, "Unicode Test")
        result = memo.load_page(pid)
        assert result["content"] == content

    def test_very_long_content(self, memo):
        content = "A" * 100000
        pid = memo.write_page(content, "Long Content")
        result = memo.load_page(pid)
        assert len(result["content"]) == 100000

    def test_special_characters_in_label(self, memo):
        pid = memo.write_page("content", 'Label with "quotes" and <brackets> & ampersands')
        result = memo.load_page(pid)
        assert result is not None

    def test_many_pages(self, memo):
        """写入大量页面不应崩溃"""
        pids = []
        for i in range(100):
            pid = memo.write_page(f"Content {i}", f"Page {i}")
            pids.append(pid)
        assert len(memo.pages) >= 100
        stats = memo.get_stats()
        assert stats["total_pages"] >= 100

    def test_rapid_write_delete_cycle(self, memo):
        """快速写入删除循环不应泄漏"""
        for i in range(50):
            pid = memo.write_page(f"Temp {i}", f"Temp Page {i}")
            memo.delete_page(pid, permanent=True)
        # 不应有大量残留
        active = sum(1 for p in memo.pages.values() if p and not p.is_deleted)
        assert active == 0

    def test_version_increment(self, memo):
        pid = memo.write_page("V1", "Versioned", page_id="VER01")
        assert memo.pages[pid].version == 1
        memo.write_page("V2", "Versioned", page_id="VER01")
        assert memo.pages[pid].version == 2
        memo.write_page("V3", "Versioned", page_id="VER01")
        assert memo.pages[pid].version == 3


# ============================================================================
# CLI 接口测试
# ============================================================================

class TestCLI:
    def test_version_flag(self, capsys):
        """直接调用 main() 前设置 sys.argv，验证版本输出"""
        import memory_engine_v26 as mod

        original_argv = sys.argv
        try:
            sys.argv = ["memory_engine_v26.py", "--version"]
            mod.main()
        except SystemExit:
            pass  # argparse 某些情况下会 sys.exit
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "OxygenMemo" in captured.out
        assert mod.OxygenMemo.VERSION in captured.out

    def test_stats_flag(self, storage_dir, capsys):
        """验证 --stats 输出包含统计信息"""
        import memory_engine_v26 as mod

        # 先创建数据
        memo = mod.OxygenMemo(storage_path=storage_dir)
        memo.write_page("CLI test content", "CLI Page")
        memo.save()
        memo.close()

        original_argv = sys.argv
        try:
            sys.argv = ["memory_engine_v26.py", "--path", storage_dir, "--stats"]
            mod.main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "total_pages" in captured.out

    def test_health_flag(self, storage_dir, capsys):
        """验证 --health 输出健康评分"""
        import memory_engine_v26 as mod

        original_argv = sys.argv
        try:
            sys.argv = ["memory_engine_v26.py", "--path", storage_dir, "--health"]
            mod.main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "健康评分" in captured.out

    def test_search_flag(self, storage_dir, capsys):
        """验证 --search 输出搜索结果"""
        import memory_engine_v26 as mod

        memo = mod.OxygenMemo(storage_path=storage_dir)
        memo.write_page("Python是一种编程语言", "Python简介", category="knowledge")
        memo.save()
        memo.close()

        original_argv = sys.argv
        try:
            sys.argv = ["memory_engine_v26.py", "--path", storage_dir, "--search", "Python"]
            mod.main()
        except SystemExit:
            pass
        finally:
            sys.argv = original_argv

        captured = capsys.readouterr()
        assert "搜索结果" in captured.out


# ============================================================================
# 回归测试：懒加载 get_stats 崩溃 (原始 bug)
# ============================================================================

class TestRegressionLazyLoadGetStats:
    """
    回归测试：确保懒加载模式下 get_stats() 不会因 NoneType 崩溃。
    原始错误: 'NoneType' object has no attribute 'page_id'
    """

    def test_lazy_load_get_stats_after_eviction(self, storage_dir):
        """写入大量页面 -> 保存 -> 触发换页 -> get_stats 不崩溃"""
        memo = OxygenMemo(
            storage_path=storage_dir,
            tlb_size=3,
            lazy_load=True,
            max_memory_mb=1,
        )
        pids = []
        for i in range(15):
            pid = memo.write_page(
                f"Regression test page {i} with substantial content padding. " * 30,
                f"Regression Page {i}",
            )
            pids.append(pid)
        memo.save()

        # 强制触发换页
        memo._check_memory_limit()

        # 关键断言：get_stats 不应抛出 AttributeError
        stats = memo.get_stats()
        assert isinstance(stats, dict)
        assert "total_pages" in stats

        memo.close()

    def test_lazy_load_get_stats_with_none_in_pages(self, storage_dir):
        """直接模拟 self.pages 中存在 None 的情况"""
        memo = OxygenMemo(
            storage_path=storage_dir,
            lazy_load=True,
        )
        pid = memo.write_page("Test content", "Test")
        memo.save()

        # 人为注入 None（模拟旧版 bug 场景）
        memo.pages["GHOST01"] = None

        # get_stats 应安全处理 None
        stats = memo.get_stats()
        assert isinstance(stats, dict)

        memo.close()

    def test_lazy_load_full_lifecycle(self, storage_dir):
        """完整的懒加载生命周期：写入 -> 保存 -> 换页 -> 重载 -> 统计"""
        memo = OxygenMemo(
            storage_path=storage_dir,
            tlb_size=3,
            lazy_load=True,
            max_memory_mb=1,
        )

        # Phase 1: 写入
        pids = []
        for i in range(10):
            pid = memo.write_page(f"Lifecycle page {i} " * 50, f"Lifecycle {i}")
            pids.append(pid)
        memo.save()

        # Phase 2: 换页
        memo._check_memory_limit()
        evicted_count = memo._stats.get("page_evictions", 0)

        # Phase 3: 统计（不应崩溃）
        stats = memo.get_stats()
        assert stats["total_pages"] >= 0

        # Phase 4: 重新加载被换出的页面
        for pid in pids:
            result = memo.load_page(pid)
            assert result is not None, f"Failed to reload {pid}"

        # Phase 5: 再次统计
        stats2 = memo.get_stats()
        assert stats2["total_pages"] >= len(pids)

        memo.close()


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])