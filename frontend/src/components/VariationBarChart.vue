<script setup>
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

// As propriedades que este componente aceita
defineProps({
  chartData: {
    type: Object,
    required: true
  },
  chartOptions: {
    type: Object,
    default: () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.dataset.label}: ${context.parsed.y.toFixed(2)}%`;
            }
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return value + '%';
            }
          }
        },
        x: {
          ticks: {
            maxRotation: 45,
            minRotation: 0
          }
        }
      }
    })
  }
})
</script>

<template>
  <Bar :data="chartData" :options="chartOptions" />
</template>
