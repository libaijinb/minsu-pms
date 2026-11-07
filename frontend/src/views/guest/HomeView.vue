<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { getCalendar, listListings } from '../../api/listings'
import ListingCard from '../../components/ListingCard.vue'
import dayjs from 'dayjs'

/**
 * C 端首页：现代消费网站布局——
 * ① Hero 大标题 + 搜索栏（城市/日期/人数）
 * ② 类型筛选 chips
 * ③ 房源卡片网格（并发拉日历算最低价）
 */
const listings = ref([])
const minPrices = ref({})  // listingId -> 当月最低可订价
const loading = ref(false)
const total = ref(0)
const page = ref(1)

const search = reactive({ city: '', type: '', guests: 1 })

// 从列表数据提取城市选项（教学项目数据量小，前端去重即可）
const cities = computed(() => [...new Set(listings.value.map((l) => l.city).filter(Boolean))])

async function loadData() {
  loading.value = true
  try {
    const params = { page: page.value, ordering: '-rating' }
    if (search.city) params.city = search.city
    if (search.type) params.type = search.type
    const data = await listListings(params)
    listings.value = data.results
    total.value = data.count
    // 并发拉每个房源未来 30 天日历，取最低可订价（3 个房源可接受，数据量大应改后端聚合）
    await Promise.all(listings.value.map(async (l) => {
      try {
        const start = dayjs().format('YYYY-MM-DD')
        const end = dayjs().add(30, 'day').format('YYYY-MM-DD')
        const rows = await getCalendar(l.id, { start, end })
        const prices = rows.filter((r) => r.status === 'available' && r.price > 0).map((r) => r.price)
        if (prices.length) minPrices.value[l.id] = Math.min(...prices)
      } catch { /* 单个房源日历失败不影响列表 */ }
    }))
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  loadData()
}

onMounted(loadData)
</script>

<template>
  <div class="home">
    <!-- Hero：大标题 + 搜索栏 -->
    <section class="hero">
      <div class="container">
        <h1 class="hero-title">发现旅途中的<em>好住之处</em></h1>
        <p class="hero-sub">精选民宿，真实评价，随时可订</p>

        <div class="search-bar lift">
          <div class="search-item">
            <label>目的地</label>
            <el-select v-model="search.city" placeholder="不限城市" size="large" clearable filterable @change="onSearch">
              <el-option v-for="c in cities" :key="c" :label="c" :value="c" />
            </el-select>
          </div>
          <div class="search-divider"></div>
          <div class="search-item">
            <label>入住人数</label>
            <el-select v-model="search.guests" size="large" @change="onSearch">
              <el-option :value="1" label="1 位" />
              <el-option :value="2" label="2 位" />
              <el-option :value="3" label="3 位" />
              <el-option :value="4" label="4 位及以上" />
            </el-select>
          </div>
          <div class="search-divider"></div>
          <div class="search-item search-types">
            <label>房源类型</label>
            <div class="type-chips">
              <span :class="{ chip: true, active: search.type === '' }" @click="search.type = ''; onSearch()">不限</span>
              <span :class="{ chip: true, active: search.type === 'whole' }" @click="search.type = 'whole'; onSearch()">整套</span>
              <span :class="{ chip: true, active: search.type === 'room' }" @click="search.type = 'room'; onSearch()">独立房间</span>
              <span :class="{ chip: true, active: search.type === 'share' }" @click="search.type = 'share'; onSearch()">合租</span>
            </div>
          </div>
          <el-button class="search-btn" type="primary" round @click="onSearch">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
        </div>
      </div>
    </section>

    <!-- 房源网格 -->
    <section class="container section">
      <div class="section-head">
        <h2 class="section-title">{{ search.city || '热门'}}房源</h2>
        <span class="section-count">共 {{ total }} 套</span>
      </div>

      <div v-loading="loading" class="grid">
        <ListingCard v-for="l in listings" :key="l.id" :listing="l" :min-price="minPrices[l.id]" />
      </div>

      <el-empty v-if="!loading && listings.length === 0" description="暂无符合条件的房源，换个条件试试" />

      <div v-if="total > 12" class="pager">
        <el-pagination v-model:current-page="page" layout="prev, pager, next"
          :total="total" :page-size="12" @current-change="loadData" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero {
  padding: 72px 0 40px;
  background: linear-gradient(180deg, #fff5f3 0%, var(--bg) 100%);
}

.hero-title {
  font-size: 40px;
  font-weight: 800;
  color: var(--ink);
  letter-spacing: 1px;
}

.hero-sub {
  color: var(--ink-2);
  font-size: 16px;
  margin: 8px 0 28px;
}

/* 搜索栏：白浮层 + 分段，OTA 首页经典样式 */
.search-bar {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #fff;
  border-radius: 999px;
  padding: 10px 12px 10px 24px;
  box-shadow: var(--shadow);
  max-width: 860px;
}

.search-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 16px;
  flex-shrink: 0;
}
.search-item label {
  font-size: 11px;
  color: var(--ink-2);
  font-weight: 600;
}
.search-item :deep(.el-select) {
  width: 130px;
}
.search-types {
  flex: 1;
}

.search-divider {
  width: 1px;
  height: 28px;
  background: var(--line);
}

.type-chips {
  display: flex;
  gap: 6px;
}
.chip {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  background: #f3f4f6;
  color: var(--ink-2);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.chip:hover {
  background: #e5e7eb;
}
.chip.active {
  background: var(--brand-light);
  color: var(--brand);
  font-weight: 600;
}

.search-btn {
  margin-left: auto;
  padding: 12px 28px;
  font-weight: 600;
}

.section {
  padding-top: 12px;
  padding-bottom: 56px;
}

.section-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 18px;
}
.section-title {
  font-size: 22px;
  font-weight: 700;
}
.section-count {
  color: var(--ink-2);
  font-size: 13px;
}

/* 卡片网格：自适应列数 */
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 20px;
  min-height: 200px;
}

.pager {
  display: flex;
  justify-content: center;
  margin-top: 28px;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 28px;
  }
  .search-bar {
    border-radius: var(--radius);
    flex-wrap: wrap;
    gap: 8px;
    padding: 16px;
  }
  .search-divider {
    display: none;
  }
  .search-item {
    padding: 0 4px;
  }
  .search-btn {
    width: 100%;
    margin-left: 0;
  }
}
</style>
