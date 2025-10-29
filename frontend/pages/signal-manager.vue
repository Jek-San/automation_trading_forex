<template>
  <div
    class="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 sm:p-6 lg:p-8"
  >
    <!-- Header -->
    <header class="mb-8">
      <div
        class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6"
      >
        <div>
          <h1
            class="text-3xl sm:text-4xl font-bold text-white mb-2 bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent"
          >
            Signal Manager
          </h1>
          <p class="text-slate-400 text-sm">
            Monitor and manage all trading signals
          </p>
        </div>
        <button
          @click="showAddModal = true"
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
              d="M12 4v16m8-8H4"
            />
          </svg>
          Add Signal
        </button>
      </div>

      <!-- Stats Cards -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div
          class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-xl p-4 shadow-xl"
        >
          <div class="flex items-center justify-between mb-2">
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
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
              />
            </svg>
            <span class="text-xs font-medium text-blue-400">All</span>
          </div>
          <p class="text-2xl font-bold text-white">{{ stats.total }}</p>
          <p class="text-slate-400 text-xs mt-1">Total Signals</p>
        </div>

        <div
          class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-xl p-4 shadow-xl"
        >
          <div class="flex items-center justify-between mb-2">
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
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span class="text-xs font-medium text-amber-400">Active</span>
          </div>
          <p class="text-2xl font-bold text-white">{{ stats.pending }}</p>
          <p class="text-slate-400 text-xs mt-1">Pending</p>
        </div>

        <div
          class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-xl p-4 shadow-xl"
        >
          <div class="flex items-center justify-between mb-2">
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
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span class="text-xs font-medium text-green-400">Success</span>
          </div>
          <p class="text-2xl font-bold text-white">{{ stats.executed }}</p>
          <p class="text-slate-400 text-xs mt-1">Executed</p>
        </div>

        <div
          class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-xl p-4 shadow-xl"
        >
          <div class="flex items-center justify-between mb-2">
            <svg
              class="w-5 h-5 text-red-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span class="text-xs font-medium text-red-400">Failed</span>
          </div>
          <p class="text-2xl font-bold text-white">{{ stats.rejected }}</p>
          <p class="text-slate-400 text-xs mt-1">Rejected</p>
        </div>
      </div>
    </header>

    <!-- Filters and Search -->
    <div
      class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 shadow-xl mb-6"
    >
      <div class="flex flex-col sm:flex-row gap-4">
        <!-- Search -->
        <div class="flex-1 relative">
          <svg
            class="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            v-model="searchTerm"
            type="text"
            placeholder="Search by pair..."
            class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl pl-10 pr-4 py-2.5 text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all"
          />
        </div>

        <!-- Filter -->
        <div class="relative">
          <svg
            class="w-5 h-5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
            />
          </svg>
          <select
            v-model="filterStatus"
            class="bg-slate-800/50 border border-slate-700/50 rounded-xl pl-10 pr-8 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 transition-all appearance-none cursor-pointer"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="executed">Executed</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Signals Table -->
    <div
      class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl shadow-xl overflow-hidden"
    >
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-slate-700">
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Pair
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Action
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Entry
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                TP
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                SL
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Risk:Reward
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Volume
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Status
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Source
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Time
              </th>
              <th
                class="py-4 px-6 text-left text-slate-400 font-medium text-sm"
              >
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="signal in filteredSignals"
              :key="signal.id"
              class="border-b border-slate-800 hover:bg-slate-800/50 transition-colors"
            >
              <td class="py-4 px-6">
                <span class="text-white font-semibold">{{ signal.pair }}</span>
              </td>
              <td class="py-4 px-6">
                <div class="flex items-center gap-2">
                  <svg
                    v-if="signal.action === 'BUY'"
                    class="w-4 h-4 text-green-400"
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
                  <svg
                    v-else
                    class="w-4 h-4 text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"
                    />
                  </svg>
                  <span
                    :class="`px-2.5 py-1 rounded-lg text-xs font-semibold ${
                      signal.action === 'BUY'
                        ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                        : 'bg-red-500/20 text-red-400 border border-red-500/30'
                    }`"
                  >
                    {{ signal.action }}
                  </span>
                </div>
              </td>
              <td class="py-4 px-6 text-slate-300 font-medium">
                {{ signal.entryPrice }}
              </td>
              <td class="py-4 px-6 text-green-400 font-medium">
                {{ signal.tp }}
              </td>
              <td class="py-4 px-6 text-red-400 font-medium">
                {{ signal.sl }}
              </td>
              <td class="py-4 px-6">
                <span
                  class="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-md font-medium"
                >
                  {{ signal.riskReward }}
                </span>
              </td>
              <td class="py-4 px-6 text-slate-300">{{ signal.volume }}</td>
              <td class="py-4 px-6">
                <div class="flex items-center gap-2">
                  <svg
                    v-if="signal.status === 'pending'"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <svg
                    v-else-if="signal.status === 'executed'"
                    class="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
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
                      d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <span
                    :class="`px-2.5 py-1 rounded-lg text-xs font-semibold border ${getStatusColor(signal.status)}`"
                  >
                    {{ signal.status }}
                  </span>
                </div>
              </td>
              <td class="py-4 px-6">
                <span
                  class="px-2 py-1 bg-slate-700/50 text-slate-300 text-xs rounded-md"
                >
                  {{ signal.source }}
                </span>
              </td>
              <td class="py-4 px-6 text-slate-400 text-sm whitespace-nowrap">
                {{ signal.timestamp }}
              </td>
              <td class="py-4 px-6">
                <div class="flex items-center gap-2">
                  <button
                    class="p-2 bg-blue-500/10 text-blue-400 rounded-lg hover:bg-blue-500/20 transition-all"
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
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </button>
                  <button
                    @click="deleteSignal(signal.id)"
                    class="p-2 bg-red-500/10 text-red-400 rounded-lg hover:bg-red-500/20 transition-all"
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
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <div v-if="filteredSignals.length === 0" class="text-center py-12">
          <svg
            class="w-12 h-12 text-slate-600 mx-auto mb-3"
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
          <p class="text-slate-400 text-lg font-medium">No signals found</p>
          <p class="text-slate-500 text-sm mt-1">
            Try adjusting your search or filter criteria
          </p>
        </div>
      </div>
    </div>

    <!-- Add Signal Modal -->
    <div
      v-if="showAddModal"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 z-50"
      @click.self="showAddModal = false"
    >
      <div
        class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 rounded-2xl p-6 max-w-2xl w-full shadow-2xl"
      >
        <div class="flex items-center justify-between mb-6">
          <h2 class="text-2xl font-bold text-white">Add New Signal</h2>
          <button
            @click="showAddModal = false"
            class="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-all"
          >
            <svg
              class="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                stroke-linecap="round"
                stroke-linejoin="round"
                stroke-width="2"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Pair</label
            >
            <input
              v-model="newSignal.pair"
              type="text"
              placeholder="XAUUSD"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>

          <div>
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Action</label
            >
            <select
              v-model="newSignal.action"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option>BUY</option>
              <option>SELL</option>
            </select>
          </div>

          <div>
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Entry Price</label
            >
            <input
              v-model="newSignal.entryPrice"
              type="number"
              step="0.01"
              placeholder="2030.50"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>

          <div>
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Take Profit</label
            >
            <input
              v-model="newSignal.tp"
              type="number"
              step="0.01"
              placeholder="2033.50"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>

          <div>
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Stop Loss</label
            >
            <input
              v-model="newSignal.sl"
              type="number"
              step="0.01"
              placeholder="2028.00"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>

          <div>
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Volume</label
            >
            <input
              v-model="newSignal.volume"
              type="number"
              step="0.01"
              placeholder="0.1"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>

          <div class="sm:col-span-2">
            <label class="block text-slate-400 text-sm font-medium mb-2"
              >Source</label
            >
            <select
              v-model="newSignal.source"
              class="w-full bg-slate-800/50 border border-slate-700/50 rounded-xl px-4 py-2.5 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option>Telegram</option>
              <option>Manual</option>
              <option>Algorithm</option>
            </select>
          </div>
        </div>

        <div class="flex gap-3 mt-6">
          <button
            @click="showAddModal = false"
            class="flex-1 px-4 py-2.5 bg-slate-700 text-white rounded-xl hover:bg-slate-600 transition-all font-medium"
          >
            Cancel
          </button>
          <button
            @click="addSignal"
            class="flex-1 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all font-medium shadow-lg shadow-blue-500/20"
          >
            Add Signal
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"

const signals = ref([
  {
    id: 1,
    pair: "XAUUSD",
    action: "BUY",
    entryPrice: 2030.5,
    tp: 2033.5,
    sl: 2028.0,
    status: "pending",
    timestamp: "2025-10-09 09:15:00",
    source: "Telegram",
    volume: 0.1,
    riskReward: "1:1.75",
  },
  {
    id: 2,
    pair: "XAUUSD",
    action: "SELL",
    entryPrice: 2032.0,
    tp: 2025.0,
    sl: 2035.0,
    status: "executed",
    timestamp: "2025-10-09 08:45:00",
    source: "Telegram",
    volume: 0.1,
    riskReward: "1:2.33",
  },
  {
    id: 3,
    pair: "EURUSD",
    action: "BUY",
    entryPrice: 1.085,
    tp: 1.089,
    sl: 1.082,
    status: "pending",
    timestamp: "2025-10-09 10:30:00",
    source: "Manual",
    volume: 0.2,
    riskReward: "1:1.33",
  },
  {
    id: 4,
    pair: "GBPUSD",
    action: "SELL",
    entryPrice: 1.265,
    tp: 1.26,
    sl: 1.268,
    status: "rejected",
    timestamp: "2025-10-09 07:20:00",
    source: "Telegram",
    volume: 0.15,
    riskReward: "1:1.67",
  },
  {
    id: 5,
    pair: "XAUUSD",
    action: "BUY",
    entryPrice: 2028.75,
    tp: 2035.0,
    sl: 2025.0,
    status: "executed",
    timestamp: "2025-10-09 06:10:00",
    source: "Manual",
    volume: 0.1,
    riskReward: "1:1.67",
  },
])

const searchTerm = ref("")
const filterStatus = ref("all")
const showAddModal = ref(false)

const newSignal = ref({
  pair: "",
  action: "BUY",
  entryPrice: "",
  tp: "",
  sl: "",
  volume: "",
  source: "Telegram",
})

const getStatusColor = (status) => {
  switch (status) {
    case "pending":
      return "bg-amber-500/20 text-amber-400 border-amber-500/30"
    case "executed":
      return "bg-green-500/20 text-green-400 border-green-500/30"
    case "rejected":
      return "bg-red-500/20 text-red-400 border-red-500/30"
    default:
      return "bg-slate-500/20 text-slate-400 border-slate-500/30"
  }
}

const filteredSignals = computed(() => {
  return signals.value.filter((signal) => {
    const matchesSearch = signal.pair
      .toLowerCase()
      .includes(searchTerm.value.toLowerCase())
    const matchesFilter =
      filterStatus.value === "all" || signal.status === filterStatus.value
    return matchesSearch && matchesFilter
  })
})

const stats = computed(() => ({
  total: signals.value.length,
  pending: signals.value.filter((s) => s.status === "pending").length,
  executed: signals.value.filter((s) => s.status === "executed").length,
  rejected: signals.value.filter((s) => s.status === "rejected").length,
}))

const addSignal = () => {
  const riskAmount = Math.abs(
    parseFloat(newSignal.value.entryPrice) - parseFloat(newSignal.value.sl)
  )
  const rewardAmount = Math.abs(
    parseFloat(newSignal.value.tp) - parseFloat(newSignal.value.entryPrice)
  )
  const riskReward = `1:${(rewardAmount / riskAmount).toFixed(2)}`

  signals.value.push({
    id: signals.value.length + 1,
    pair: newSignal.value.pair,
    action: newSignal.value.action,
    entryPrice: parseFloat(newSignal.value.entryPrice),
    tp: parseFloat(newSignal.value.tp),
    sl: parseFloat(newSignal.value.sl),
    status: "pending",
    timestamp: new Date().toISOString().slice(0, 19).replace("T", " "),
    source: newSignal.value.source,
    volume: parseFloat(newSignal.value.volume),
    riskReward: riskReward,
  })

  // Reset form
  newSignal.value = {
    pair: "",
    action: "BUY",
    entryPrice: "",
    tp: "",
    sl: "",
    volume: "",
    source: "Telegram",
  }

  showAddModal.value = false
}

const deleteSignal = (id) => {
  signals.value = signals.value.filter((s) => s.id !== id)
}
</script>
