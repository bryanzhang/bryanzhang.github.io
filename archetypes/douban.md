---
title: "{{ replace .File.ContentBaseName "-" " " | title }}"
date: 2016-01-01            # 豆瓣原发表日期，决定排序与页面显示
migrated: {{ .Date | time.Format "2006-01-02" }}   # 迁移日期
original:
  platform: 豆瓣
  url: ""                   # 豆瓣原文链接
  note: ""                  # 可选：如"内容未改动"或"迁移时修正了错别字"
draft: true
tags: []
summary: ""
math: false
---

