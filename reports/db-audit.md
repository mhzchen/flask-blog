# 数据库巡检报告

巡检对象：**主库**

## 表与行数

| 表 | 行数 |
|---|--:|
| `alembic_version` | 1 |
| `categories` | 3 |
| `comments` | 3 |
| `favorites` | 1 |
| `post_likes` | 0 |
| `post_tags` | 3 |
| `posts` | 5 |
| `tags` | 3 |
| `users` | 8 |

## 索引清单（冗余项 ★）

- `alembic_version`.**PRIMARY** 列=['version_num'] 唯一=是 类型=BTREE
- `categories`.**name** 列=['name'] 唯一=是 类型=BTREE
- `categories`.**PRIMARY** 列=['id'] 唯一=是 类型=BTREE
- `categories`.**slug** 列=['slug'] 唯一=是 类型=BTREE
- `comments`.**parent_id** 列=['parent_id'] 唯一=否 类型=BTREE
- `comments`.**post_id** 列=['post_id'] 唯一=否 类型=BTREE
- `comments`.**PRIMARY** 列=['id'] 唯一=是 类型=BTREE
- `comments`.**user_id** 列=['user_id'] 唯一=否 类型=BTREE
- `favorites`.**post_id** 列=['post_id'] 唯一=否 类型=BTREE
- `favorites`.**PRIMARY** 列=['user_id', 'post_id'] 唯一=是 类型=BTREE
- `post_likes`.**post_id** 列=['post_id'] 唯一=否 类型=BTREE
- `post_likes`.**PRIMARY** 列=['user_id', 'post_id'] 唯一=是 类型=BTREE
- `post_tags`.**PRIMARY** 列=['post_id', 'tag_id'] 唯一=是 类型=BTREE
- `post_tags`.**tag_id** 列=['tag_id'] 唯一=否 类型=BTREE
- `posts`.**ix_posts_category_id** 列=['category_id'] 唯一=否 类型=BTREE
- `posts`.**ix_posts_content_fulltext** 列=['content'] 唯一=否 类型=FULLTEXT ★冗余
- `posts`.**ix_posts_created_at** 列=['created_at'] 唯一=否 类型=BTREE
- `posts`.**ix_posts_search_fulltext** 列=['title', 'summary', 'content'] 唯一=否 类型=FULLTEXT
- `posts`.**ix_posts_title** 列=['title'] 唯一=否 类型=BTREE
- `posts`.**PRIMARY** 列=['id'] 唯一=是 类型=BTREE
- `posts`.**slug** 列=['slug'] 唯一=是 类型=BTREE
- `tags`.**name** 列=['name'] 唯一=是 类型=BTREE
- `tags`.**PRIMARY** 列=['id'] 唯一=是 类型=BTREE
- `users`.**email** 列=['email'] 唯一=是 类型=BTREE
- `users`.**PRIMARY** 列=['id'] 唯一=是 类型=BTREE
- `users`.**username** 列=['username'] 唯一=是 类型=BTREE

## 冗余索引检测

- `posts`.**ix_posts_content_fulltext** 被 `ix_posts_search_fulltext` 覆盖 → 建议删除（FULLTEXT 列集合被更大 FULLTEXT 覆盖，属冗余）

## EXPLAIN 基线

### 列表-offset分页
```
  1 | SIMPLE | p | None | ALL | None | None | None
```

### 列表-keyset游标
```
  1 | SIMPLE | p | None | ALL | None | None | None
```

### 详情-主键
```
  1 | SIMPLE | posts | None | const | PRIMARY | PRIMARY | 4
```

### 分类筛选
```
  1 | SIMPLE | p | None | ref | ix_posts_category_id | ix_posts_category_id | 4
```

### 全文搜索
```
  1 | SIMPLE | posts | None | fulltext | ix_posts_search_fulltext | ix_posts_search_fulltext | 0
```

### 评论列表
```
  1 | SIMPLE | comments | None | ref | post_id | post_id | 4
```

### 点赞反查
```
  1 | SIMPLE | post_likes | None | ref | post_id | post_id | 4
```

## 从库一致性

- 未配置从库（无 `DATABASE_URL_SLAVE`），当前为单库模式，无一致性校验对象；配好从库后以 `--slave` 重跑本脚本即可对比各表行数。
