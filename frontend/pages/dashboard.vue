<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 sm:p-6 lg:p-8"
  >
    <!-- Header -->
    <header
      class="mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
    >
      <div>
        <h1
          class="text-3xl sm:text-4xl font-bold mb-2 bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent"
        >
          Trading Automation
        </h1>
        <p class="text-slate-400 text-sm">
          Real-time market monitoring & execution
        </p>
      </div>
      <button
        class="px-5 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all duration-200 shadow-lg shadow-blue-500/20 flex items-center gap-2 font-medium"
      >
        <svg
          class="w-4 h-4"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="2"
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        Refresh All
      </button>
    </header>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <div
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-5 shadow-xl"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="p-2 bg-green-500/10 rounded-lg">
            <svg
              class="w-5 h-5 text-green-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <span class="text-xs font-medium text-green-400">+12.3%</span>
        </div>
        <p class="text-slate-400 text-sm mb-1">Total P&L</p>
        <p
          :class="`text-2xl font-bold ${totalProfit >= 0 ? 'text-green-400' : 'text-red-400'}`"
        >
          ${{ totalProfit.toFixed(2) }}
        </p>
      </div>

      <div
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-5 shadow-xl"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="p-2 bg-blue-500/10 rounded-lg">
            <svg
              class="w-5 h-5 text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
              />
            </svg>
          </div>
          <span class="text-xs font-medium text-blue-400">Active</span>
        </div>
        <p class="text-slate-400 text-sm mb-1">Win Rate</p>
        <p class="text-2xl font-bold text-white">{{ winRate }}%</p>
      </div>

      <div
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-5 shadow-xl"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="p-2 bg-purple-500/10 rounded-lg">
            <svg
              class="w-5 h-5 text-purple-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
          </div>
          <span class="text-xs font-medium text-purple-400">Live</span>
        </div>
        <p class="text-slate-400 text-sm mb-1">Active Signals</p>
        <p class="text-2xl font-bold text-white">{{ activeSignalsCount }}</p>
      </div>

      <div
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-5 shadow-xl"
      >
        <div class="flex items-center justify-between mb-3">
          <div class="p-2 bg-amber-500/10 rounded-lg">
            <svg
              class="w-5 h-5 text-amber-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
          </div>
          <span class="text-xs font-medium text-amber-400">Running</span>
        </div>
        <p class="text-slate-400 text-sm mb-1">Services Online</p>
        <p class="text-2xl font-bold text-white">
          {{ runningServicesCount }}/{{ services.length }}
        </p>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Service Control -->
      <section
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-xl"
      >
        <div class="flex items-center gap-2 mb-5">
          <svg
            class="w-5 h-5 text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
          <h2 class="text-xl font-semibold text-white">Service Control</h2>
        </div>
        <div class="space-y-3">
          <div
            v-for="(service, index) in services"
            :key="service.name"
            class="flex items-center justify-between p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl hover:bg-slate-800/80 transition-all duration-200"
          >
            <div class="flex items-center gap-3">
              <div
                :class="`p-2 rounded-lg ${service.status === 'running' ? 'bg-green-500/10' : 'bg-slate-700/50'}`"
              >
                <component :is="service.icon" />
              </div>
              <div>
                <p class="font-medium text-white">{{ service.name }}</p>
                <p class="text-sm text-slate-400">{{ service.description }}</p>
              </div>
            </div>
            <div class="flex items-center gap-3">
              <div class="flex items-center gap-2">
                <span
                  :class="`w-2 h-2 rounded-full ${
                    service.status === 'running'
                      ? 'bg-green-400 animate-pulse'
                      : 'bg-slate-500'
                  }`"
                ></span>
                <span class="text-xs text-slate-400 hidden sm:inline">
                  {{ service.status }}
                </span>
              </div>
              <button
                :class="`p-2 text-sm rounded-lg transition-all duration-200 ${
                  service.status === 'running'
                    ? 'bg-red-500/10 text-red-400 hover:bg-red-500/20'
                    : 'bg-green-500/10 text-green-400 hover:bg-green-500/20'
                }`"
                @click="toggleService(index)"
              >
                <svg
                  v-if="service.status === 'running'"
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"
                  />
                </svg>
                <svg
                  v-else
                  class="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    stroke-width="2"
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Signal Manager -->
      <section
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-xl"
      >
        <div class="flex items-center gap-2 mb-5">
          <svg
            class="w-5 h-5 text-purple-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
            />
          </svg>
          <h2 class="text-xl font-semibold text-white">Signal Manager</h2>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="py-3 text-left text-slate-400 font-medium">Time</th>
                <th class="py-3 text-left text-slate-400 font-medium">Pair</th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Action
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">TP</th>
                <th class="py-3 text-left text-slate-400 font-medium">SL</th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Try Place
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Status
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">Type</th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Risk:Reward
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Source
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="signal in paginatedSignals"
                :key="signal.id"
                class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors"
              >
                <td class="py-3 text-white font-medium">
                  {{ formatTime(signal.createdAt) }}
                </td>
                <td class="py-3 text-white font-medium">{{ signal.pair }}</td>
                <td class="py-3">
                  <span
                    :class="`px-2 py-1 rounded-md text-xs font-medium ${
                      signal.action === 'BUY'
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`"
                  >
                    {{ signal.action }}
                  </span>
                </td>
                <td class="py-3 text-slate-300">{{ signal.tp }}</td>
                <td class="py-3 text-slate-300">{{ signal.sl }}</td>
                <td class="py-3 text-slate-300">{{ signal.tryPlace }}</td>
                <td class="py-3">
                  <span
                    :class="`px-2 py-1 rounded-md text-xs font-medium ${
                      signal.status === 'pending'
                        ? 'bg-amber-500/20 text-amber-400'
                        : signal.status === 'placed'
                          ? 'bg-green-500/20 text-green-400'
                          : signal.status === 'failed'
                            ? 'bg-red-500/20 text-red-400'
                            : 'bg-slate-600/20 text-slate-400'
                    }`"
                  >
                    {{ signal.status }}
                  </span>
                </td>
                <td class="py-3 text-slate-300">{{ signal.typeOrder }}</td>
                <td class="py-3 text-slate-300">{{ signal.rr }}</td>
                <td class="py-3 text-slate-300">{{ signal.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination Controls -->
        <PaginationControls
          :currentPage="currentPage"
          :totalPages="totalPages"
          @prev="prevPage"
          @next="nextPage"
        />
      </section>

      <!-- Trade History -->
      <section
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-xl"
      >
        <div class="flex items-center gap-2 mb-5">
          <svg
            class="w-5 h-5 text-green-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h2 class="text-xl font-semibold text-white">Trade History</h2>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="py-3 text-left text-slate-400 font-medium">
                  Symbol
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Profit
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Result
                </th>
                <th class="py-3 text-left text-slate-400 font-medium">Time</th>
                <th class="py-3 text-left text-slate-400 font-medium">
                  Source
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="trade in trades"
                :key="trade.id"
                class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors"
              >
                <td class="py-3 text-white font-medium">{{ trade.symbol }}</td>
                <td
                  :class="`py-3 font-semibold ${trade.profit > 0 ? 'text-green-400' : 'text-red-400'}`"
                >
                  ${{ (trade.profit ?? 0).toFixed(2) }}
                </td>
                <td class="py-3">
                  <span
                    :class="`px-2 py-1 rounded-md text-xs font-medium ${
                      trade.profit > 0
                        ? 'bg-green-500/20 text-green-400'
                        : trade.profit < 0
                          ? 'bg-red-500/20 text-red-400'
                          : 'bg-yellow-500/20 text-yellow-400'
                    }`"
                  >
                    {{
                      trade.profit > 0
                        ? "WIN"
                        : trade.profit < 0
                          ? "LOSE"
                          : "Still Counting"
                    }}
                  </span>
                </td>

                <td class="py-3 text-slate-400">{{ trade.time }}</td>
                <td class="py-3 text-slate-400">{{ trade.source }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Market Data -->
      <section
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-xl"
      >
        <div class="flex items-center gap-2 mb-5">
          <svg
            class="w-5 h-5 text-blue-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
            />
          </svg>
          <h2 class="text-xl font-semibold text-white">Market Data</h2>
          <span
            class="ml-auto text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded-md"
            >XAUUSD M15</span
          >
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div
            class="bg-slate-800/50 border border-slate-700/50 p-4 rounded-xl"
          >
            <p class="text-slate-400 text-sm mb-2">Open</p>
            <p class="font-bold text-white text-lg">{{ market.open }}</p>
          </div>
          <div
            class="bg-slate-800/50 border border-slate-700/50 p-4 rounded-xl"
          >
            <p class="text-slate-400 text-sm mb-2">Close</p>
            <p class="font-bold text-white text-lg">{{ market.close }}</p>
          </div>
          <div
            class="bg-slate-800/50 border border-slate-700/50 p-4 rounded-xl"
          >
            <p class="text-slate-400 text-sm mb-2">High</p>
            <p class="font-bold text-green-400 text-lg">{{ market.high }}</p>
          </div>
          <div
            class="bg-slate-800/50 border border-slate-700/50 p-4 rounded-xl"
          >
            <p class="text-slate-400 text-sm mb-2">Low</p>
            <p class="font-bold text-red-400 text-lg">{{ market.low }}</p>
          </div>
        </div>
      </section>

      <!-- Trailing & Telegram -->
      <section
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-xl lg:col-span-2"
      >
        <div class="flex items-center gap-2 mb-5">
          <svg
            class="w-5 h-5 text-amber-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          <h2 class="text-xl font-semibold text-white">System Monitors</h2>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div
            class="p-5 bg-slate-800/50 border border-slate-700/50 rounded-xl"
          >
            <div class="flex items-center justify-between mb-3">
              <h3 class="font-semibold text-white">Trailing Stop</h3>
              <span
                class="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-md font-medium"
                >Active</span
              >
            </div>
            <p class="text-sm text-slate-400">
              Last updated:
              <span class="text-slate-300">{{ trailing.lastUpdate }}</span>
            </p>
          </div>
          <div
            class="p-5 bg-slate-800/50 border border-slate-700/50 rounded-xl"
          >
            <div class="flex items-center justify-between mb-3">
              <h3 class="font-semibold text-white">Telegram Parser</h3>
              <span
                class="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-md font-medium"
                >Connected</span
              >
            </div>
            <p class="text-sm text-slate-400">
              Last message:
              <span class="text-slate-300">{{ telegram.lastMessage }}</span>
            </p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, h } from "vue"

// Service icon components

const services = ref([])

async function fetchServices() {
  const response = await useApi("services", "GET")
  services.value = response
}

const signals = ref([])
const {
  currentPage,
  totalPages,
  paginatedData: paginatedSignals,
  nextPage,
  prevPage,
} = usePagination(signals, 10)
// Format time function
function formatTime(dateString) {
  const date = new Date(dateString)

  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const year = date.getFullYear()

  const hours = String(date.getHours()).padStart(2, "0")
  const minutes = String(date.getMinutes()).padStart(2, "0")

  return `${day}/${month}/${year} ${hours}:${minutes}`
}
async function fetchSignals() {
  try {
    const response = await useApi("signals", { method: "GET" })
    signals.value = response.map((item) => ({
      id: item.id,
      pair: item.instrument,
      action: item.action.toUpperCase(),
      tp: item.tp1, // or average between tp1/tp2 if you prefer
      sl: item.sl,
      tryPlace: item.price_entry,
      status: item.status === "completed" ? "placed" : item.status,
      typeOrder: item.type_order,
      source: item.source,
      createdAt: item.created_at,
      entry: item.price_entry,
      rr: `${item.risk}:${item.reward}`,
    }))
  } catch (err) {
    console.error("Failed to fetch signals:", err)
  }
}

const trades = ref([
  { id: 1, symbol: "XAUUSD", profit: 35.2, time: "10:22" },
  { id: 2, symbol: "XAUUSD", profit: -12.5, time: "11:45" },
  { id: 3, symbol: "XAUUSD", profit: 22.8, time: "12:10" },
  { id: 4, symbol: "XAUUSD", profit: -8.3, time: "13:30" },
])

async function fetchTrades() {
  try {
    const response = await useApi("trades", { method: "GET" })
    console.log(response)
    trades.value = response.map((item) => ({
      id: item.trade_position_id,
      symbol: item.symbol,
      profit: item.profit,
      time: item.trade_time,
      source: item.source,
    }))
  } catch (err) {
    console.error("Failed to fetch signals:", err)
  }
}

const market = ref({
  open: 2030.12,
  high: 2035.55,
  low: 2028.4,
  close: 2032.78,
})

const trailing = ref({ lastUpdate: "2025-10-09 09:20" })
const telegram = ref({ lastMessage: "2025-10-09 09:25" })

const totalProfit = computed(() => {
  return trades.value.reduce((sum, trade) => sum + trade.profit, 0)
})

const winRate = computed(() => {
  if (!trades.value.length) return 0
  const wins = trades.value.filter((t) => t.profit > 0).length
  return ((wins / trades.value.length) * 100).toFixed(0)
})

const activeSignalsCount = computed(() => {
  return signals.value.filter((s) => s.status === "pending").length
})

const runningServicesCount = computed(() => {
  return services.value.filter((s) => s.status === "running").length
})

async function toggleService(index) {
  const service = services.value[index]
  const isRunning = service.status === "running"

  // Optimistic UI update (instant feedback)
  service.status = isRunning ? "stopped" : "running"

  try {
    const endpoint = `services/${service.name}/${isRunning ? "stop" : "start"}`
    await useApi(endpoint, { method: "POST" })
    console.log(
      `✅ ${service.name} ${isRunning ? "stopped" : "started"} successfully`
    )
    fetchServices()
  } catch (err) {
    console.error(`❌ Failed to toggle ${service.name}:`, err)
    // revert UI if error
    service.status = isRunning ? "running" : "stopped"
  }
}
onMounted(() => {
  // initial load
  fetchServices()
  fetchSignals()
  fetchTrades()

  // auto refresh every 5 seconds
  const interval = setInterval(() => {
    fetchServices()
    fetchSignals()
    fetchTrades()
  }, 5000)

  // cleanup when component unmounts
  onUnmounted(() => clearInterval(interval))
})
</script>
