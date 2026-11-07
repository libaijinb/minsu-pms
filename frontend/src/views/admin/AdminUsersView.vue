<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { assignRoles, listRoles, listUsers } from '../../api/auth'

/**
 * 用户管理（运营）：
 * - 用户列表：按角色筛选 + 关键词搜索（用户名/手机号）
 * - 分配角色：覆盖式赋值（BR-USR-02），一个用户可多角色
 */
const users = ref([])
const roles = ref([])
const loading = ref(false)
const filterRole = ref('')
const keyword = ref('')

// 角色分配弹窗
const roleDialog = ref(false)
const current = ref(null)
const checkedRoles = ref([])

async function loadData() {
  loading.value = true
  try {
    const data = await listUsers({ role: filterRole.value || undefined, keyword: keyword.value || undefined, page_size: 100 })
    users.value = data.results || []
  } finally {
    loading.value = false
  }
}

function openAssign(row) {
  current.value = row
  checkedRoles.value = (row.roles || []).map((r) => r.code)
  roleDialog.value = true
}

async function doAssign() {
  if (!checkedRoles.value.length) {
    ElMessage.warning('至少分配一个角色')
    return
  }
  await assignRoles(current.value.id, checkedRoles.value)
  ElMessage.success(`${current.value.username} 的角色已更新`)
  roleDialog.value = false
  loadData()
}

onMounted(async () => {
  const roleData = await listRoles()
  roles.value = roleData
  await loadData()
})
</script>

<template>
  <div class="page">
    <div class="toolbar">
      <h2 class="page-title">用户管理</h2>
      <div class="ops">
        <el-input v-model="keyword" placeholder="搜索用户名/手机号" clearable style="width: 200px"
          @change="loadData" @clear="loadData" />
        <el-select v-model="filterRole" placeholder="角色筛选" clearable style="width: 130px" @change="loadData">
          <el-option v-for="r in roles" :key="r.code" :label="r.label" :value="r.code" />
        </el-select>
      </div>
    </div>

    <el-table v-loading="loading" :data="users" stripe>
      <el-table-column label="用户" min-width="180">
        <template #default="{ row }">
          <div class="user-cell">
            <el-avatar :size="32" :src="row.avatar">{{ (row.first_name || row.username)?.[0] }}</el-avatar>
            <div>
              <p class="name">{{ row.first_name || row.username }}</p>
              <p class="sub">@{{ row.username }}</p>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="手机号" width="130" />
      <el-table-column prop="email" label="邮箱" min-width="160" show-overflow-tooltip />
      <el-table-column label="角色" min-width="180">
        <template #default="{ row }">
          <el-tag v-for="r in row.roles" :key="r.code" size="small" class="role-tag">{{ r.label }}</el-tag>
          <span v-if="!row.roles?.length" class="muted">无角色</span>
        </template>
      </el-table-column>
      <el-table-column prop="date_joined" label="注册时间" width="170" />
      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button text type="primary" @click="openAssign(row)">分配角色</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分配角色弹窗 -->
    <el-dialog v-model="roleDialog" title="分配角色" width="400px">
      <template v-if="current">
        <p class="dialog-meta">用户：{{ current.first_name || current.username }}（@{{ current.username }}）</p>
        <el-checkbox-group v-model="checkedRoles" class="role-checks">
          <el-checkbox v-for="r in roles" :key="r.code" :value="r.code" size="large">
            {{ r.label }}
          </el-checkbox>
        </el-checkbox-group>
        <p class="dialog-tip">覆盖式保存：勾选的角色会全量替换原有角色</p>
      </template>
      <template #footer>
        <el-button @click="roleDialog = false">取消</el-button>
        <el-button type="primary" @click="doAssign">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-title {
  font-size: 18px;
  font-weight: 700;
}
.ops {
  display: flex;
  gap: 10px;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.name {
  font-size: 14px;
  font-weight: 600;
}
.sub {
  font-size: 12px;
  color: var(--ink-2);
}
.muted {
  color: #9ca3af;
  font-size: 12px;
}
.role-tag {
  margin-right: 6px;
}

.dialog-meta {
  font-size: 14px;
  margin-bottom: 12px;
}
.role-checks {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dialog-tip {
  font-size: 12px;
  color: var(--ink-2);
  margin-top: 12px;
}
</style>
