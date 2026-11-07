<script setup>
/**
 * 房源卡片：C 端核心视觉单元。
 * 大图 + 评分徽章 + 收藏心形 + 标题位置 + 最低价/晚。
 * 最低价由首页加载时并发拉各房源日历计算（数据量小，N+1 可接受）。
 */
defineProps({
  listing: { type: Object, required: true },
  minPrice: { type: Number, default: null },
})

const typeLabel = { whole: '整套房源', room: '独立房间', share: '合租间' }
</script>

<template>
  <router-link :to="`/listing/${listing.id}`" class="listing-card lift">
    <div class="card-media">
      <img :src="listing.images?.[0] || '/img/listing0-0.svg'"
        :alt="listing.title" loading="lazy"
        @error="$event.target.style.display = 'none'" />
      <span class="type-badge">{{ typeLabel[listing.type] || '房源' }}</span>
      <button class="fav-btn" @click.prevent>
        <el-icon><Star /></el-icon>
      </button>
    </div>
    <div class="card-body">
      <div class="card-row">
        <span class="card-title">{{ listing.title }}</span>
        <span class="rating">
          <el-icon><Star /></el-icon>{{ listing.rating }}
        </span>
      </div>
      <p class="card-loc">{{ listing.city }} · {{ listing.district }} · 宜住{{ listing.max_guests }}人</p>
      <div class="card-tags">
        <span v-for="f in (listing.facilities || []).slice(0, 3)" :key="f" class="tag">{{ f }}</span>
      </div>
      <p class="card-price">
        <span class="price">¥{{ minPrice ?? '—' }}</span>
        <span class="unit">/晚起</span>
      </p>
    </div>
  </router-link>
</template>

<style scoped>
.listing-card {
  display: block;
  background: var(--card);
  border-radius: var(--radius);
  overflow: hidden;
  color: var(--ink);
  box-shadow: var(--shadow);
}

.card-media {
  position: relative;
  aspect-ratio: 4 / 3;
  overflow: hidden;
  background: linear-gradient(135deg, #fbc2eb, #a6c1ee);  /* 图片加载失败时露出渐变占位 */
}
.card-media img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s ease;
}
.listing-card:hover .card-media img {
  transform: scale(1.06);
}

.type-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(4px);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}

.fav-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.92);
  color: var(--ink-2);
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: color 0.2s, transform 0.2s;
}
.fav-btn:hover {
  color: var(--brand);
  transform: scale(1.12);
}

.card-body {
  padding: 14px 16px 16px;
}

.card-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
}
.card-title {
  font-weight: 600;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rating {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: var(--ink);
  font-weight: 600;
  flex-shrink: 0;
}
.rating .el-icon {
  color: #ffb400;
}

.card-loc {
  font-size: 13px;
  color: var(--ink-2);
  margin-top: 4px;
}

.card-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}
.tag {
  font-size: 11px;
  color: var(--ink-2);
  background: #f3f4f6;
  border-radius: 6px;
  padding: 2px 8px;
}

.card-price {
  margin-top: 10px;
}
.price {
  font-size: 18px;
  font-weight: 700;
  color: var(--brand);
}
.unit {
  font-size: 12px;
  color: var(--ink-2);
  margin-left: 2px;
}
</style>
