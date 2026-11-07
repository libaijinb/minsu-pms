<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getListing, getCalendar } from '../../api/listings'
import { listReviews } from '../../api/core'
import PriceCalendar from '../../components/PriceCalendar.vue'
import { useUserStore } from '../../stores/user'

/**
 * 房源详情：C 端重头戏——
 * ① 图片廊（1 大图 + 网格小图）
 * ② 标题/评分/位置/设施/描述/评价
 * ③ 右侧粘性预订卡：价格日历 + 人数 + 房费小计 + 去预订
 */
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const listing = ref(null)
const reviews = ref([])
const loading = ref(false)
const selected = ref({ checkin: '', checkout: '', nights: 0, total: 0 })
const guests = ref(2)
const showCalendar = ref(false)

const typeLabel = { whole: '整套房源', room: '独立房间', share: '合租间' }
const gallery = computed(() => {
  const imgs = listing.value?.images || []
  return imgs.length ? imgs : ['/img/listing0-0.svg']
})
const bigImage = computed(() => gallery.value[0])
const smallImages = computed(() => gallery.value.slice(1, 5))

async function loadDetail() {
  loading.value = true
  try {
    listing.value = await getListing(route.params.id)
    const data = await listReviews({ listing: route.params.id })
    reviews.value = data.results || []
  } finally {
    loading.value = false
  }
}

function onRangeChange(range) {
  selected.value = range
}

function goBooking() {
  if (!userStore.isLoggedIn) {
    ElMessage.warning('请先登录')
    router.push('/login')
    return
  }
  if (!selected.value.checkin || !selected.value.checkout) {
    ElMessage.warning('请在日历中选择入住与退房日期')
    return
  }
  router.push({
    path: `/booking/${route.params.id}`,
    query: { ci: selected.value.checkin, co: selected.value.checkout, guests: guests.value },
  })
}

onMounted(loadDetail)
</script>

<template>
  <div v-loading="loading" class="detail-page">
    <div v-if="listing" class="container">
      <h1 class="title">{{ listing.title }}</h1>
      <div class="meta-row">
        <span class="rating"><el-icon><Star /></el-icon>{{ listing.rating }} · {{ listing.rating_count }} 条评价</span>
        <span class="loc">{{ listing.city }} · {{ listing.district }} · {{ listing.address }}</span>
        <router-link to="/">← 返回发现页</router-link>
      </div>

      <!-- 图片廊：左大图 + 右 2×2 小图 -->
      <div class="gallery">
        <div class="gallery-big">
          <img :src="bigImage" :alt="listing.title"
            @error="$event.target.style.display = 'none'" />
        </div>
        <div class="gallery-grid">
          <img v-for="(img, i) in smallImages" :key="i" :src="img" :alt="`图 ${i + 2}`"
            @error="$event.target.style.display = 'none'" />
        </div>
      </div>

      <div class="content-row">
        <!-- 左：房源信息 -->
        <div class="info-col">
          <div class="info-block">
            <h2>{{ typeLabel[listing.type] }} · 宜住 {{ listing.max_guests }} 人 · {{ listing.bed_count }} 床</h2>
            <p class="desc">{{ listing.description }}</p>
          </div>

          <div class="info-block">
            <h3>设施标签</h3>
            <div class="facilities">
              <span v-for="f in listing.facilities" :key="f" class="facility">{{ f }}</span>
            </div>
          </div>

          <div class="info-block">
            <h3>客人评价（{{ reviews.length }}）</h3>
            <div v-if="reviews.length" class="review-list">
              <div v-for="r in reviews.slice(0, 4)" :key="r.id" class="review">
                <div class="review-head">
                  <el-avatar :size="28" :src="r.reviewer_avatar">{{ r.reviewer_name?.[0] }}</el-avatar>
                  <span class="review-name">{{ r.reviewer_name }}</span>
                  <el-rate :model-value="r.rating" disabled size="small" />
                </div>
                <p class="review-content">{{ r.content }}</p>
                <p v-if="r.reply" class="review-reply">房东回复：{{ r.reply }}</p>
              </div>
            </div>
            <el-empty v-else description="还没有评价，住过的人会来这里说说" :image-size="60" />
          </div>
        </div>

        <!-- 右：粘性预订卡 -->
        <div class="booking-col">
          <div class="booking-card">
            <div class="price-row">
              <span class="price">查看日历价格</span>
            </div>
            <div class="booking-fields">
              <div class="field">
                <label>入住 / 退房</label>
                <el-button class="date-btn" @click="showCalendar = true">
                  {{ selected.checkin ? `${selected.checkin} 至 ${selected.checkout || '…'}` : '选择日期' }}
                </el-button>
              </div>
              <div class="field">
                <label>入住人数</label>
                <el-select v-model="guests" style="width: 100%">
                  <el-option v-for="n in listing.max_guests" :key="n" :value="n" :label="`${n} 位`" />
                </el-select>
              </div>
            </div>
            <div v-if="selected.nights" class="summary">
              <div class="summary-row">
                <span>¥{{ Math.round(selected.total / selected.nights) }} × {{ selected.nights }} 晚</span>
                <span>¥{{ selected.total }}</span>
              </div>
              <div class="summary-row total">
                <span>房费小计</span>
                <span>¥{{ selected.total }}</span>
              </div>
            </div>
            <el-button class="book-btn" type="primary" size="large" round @click="goBooking">
              立即预订
            </el-button>
            <p class="book-tip">押金 ¥{{ listing.deposit_amount }}，退房查房无损原路退还</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 日历弹层 -->
    <el-dialog v-model="showCalendar" title="选择入住日期" width="760px" destroy-on-close>
      <PriceCalendar :listing-id="listing?.id" :months="2" @range-change="onRangeChange" />
      <template #footer>
        <span class="dialog-summary" v-if="selected.nights">
          已选 {{ selected.nights }} 晚 · 房费 ¥{{ selected.total }}
        </span>
        <el-button type="primary" round @click="showCalendar = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.detail-page {
  padding: 32px 0 64px;
}

.title {
  font-size: 26px;
  font-weight: 800;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 8px 0 20px;
  font-size: 14px;
  color: var(--ink-2);
  flex-wrap: wrap;
}
.rating {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--ink);
  font-weight: 600;
}
.rating .el-icon {
  color: #ffb400;
}
.meta-row a {
  margin-left: auto;
  font-size: 13px;
}

/* 图片廊 */
.gallery {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 8px;
  border-radius: var(--radius);
  overflow: hidden;
  height: 420px;
  background: linear-gradient(135deg, #fbc2eb, #a6c1ee);  /* 图片失败时露出渐变 */
}
.gallery-big img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.gallery-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 8px;
}
.gallery-grid img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.content-row {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 32px;
  margin-top: 28px;
  align-items: start;
}

.info-block {
  padding-bottom: 24px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 24px;
}
.info-block h2 {
  font-size: 18px;
  margin-bottom: 8px;
}
.info-block h3 {
  font-size: 16px;
  margin-bottom: 12px;
}
.desc {
  color: var(--ink-2);
  line-height: 1.7;
}

.facilities {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.facility {
  background: #f3f4f6;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--ink);
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.review-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.review-name {
  font-weight: 600;
  font-size: 14px;
}
.review-content {
  color: var(--ink-2);
  font-size: 14px;
  margin: 6px 0 0 36px;
  line-height: 1.6;
}
.review-reply {
  color: var(--ink-2);
  font-size: 13px;
  margin: 6px 0 0 36px;
  background: #f9fafb;
  border-radius: 8px;
  padding: 8px 12px;
}

/* 粘性预订卡 */
.booking-col {
  position: sticky;
  top: 88px;
}
.booking-card {
  background: #fff;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 20px;
}
.price-row {
  margin-bottom: 16px;
}
.price {
  font-size: 20px;
  font-weight: 800;
  color: var(--ink);
}

.booking-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.field label {
  display: block;
  font-size: 12px;
  color: var(--ink-2);
  font-weight: 600;
  margin-bottom: 4px;
}
.date-btn {
  width: 100%;
  justify-content: flex-start;
}

.summary {
  border-top: 1px solid var(--line);
  margin-top: 16px;
  padding-top: 12px;
}
.summary-row {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ink-2);
  margin-bottom: 6px;
}
.summary-row.total {
  color: var(--ink);
  font-weight: 700;
  font-size: 16px;
}

.book-btn {
  width: 100%;
  margin-top: 12px;
  font-weight: 700;
}
.book-tip {
  text-align: center;
  font-size: 12px;
  color: var(--ink-2);
  margin-top: 10px;
}

.dialog-summary {
  float: left;
  font-size: 14px;
  color: var(--ink);
}

@media (max-width: 900px) {
  .content-row {
    grid-template-columns: 1fr;
  }
  .booking-col {
    position: static;
  }
  .gallery {
    grid-template-columns: 1fr;
    height: auto;
  }
  .gallery-big {
    height: 280px;
  }
  .gallery-grid img {
    height: 140px;
  }
}
</style>
