<template>
  <div class="tw-space-y-3">
    <div 
      v-for="(service, index) in serviceVariationData.slice(0, 5)" 
      :key="service.service"
      class="tw-flex tw-items-center tw-justify-between tw-p-3 tw-bg-gray-50 tw-rounded-lg tw-border tw-border-gray-200"
    >
      <!-- Lado Esquerdo: Serviço -->
      <div class="tw-flex tw-items-center tw-space-x-3">
        <div class="tw-w-8 tw-h-8 tw-bg-blue-100 tw-rounded-full tw-flex tw-items-center tw-justify-center tw-text-xs tw-font-bold tw-text-blue-600">
          {{ index + 1 }}
        </div>
        <div>
          <div class="tw-font-semibold tw-text-gray-900 tw-text-sm">
            {{ service.service }}
          </div>
          <div class="tw-text-xs tw-text-gray-500">
            ${{ (service.currentCost || 0).toFixed(2) }} atual
          </div>
        </div>
      </div>
      
      <!-- Lado Direito: Variação -->
      <div class="tw-text-right">
        <div :class="['tw-font-bold tw-text-sm', 
                     service.variationPercentage >= 0 ? 'tw-text-red-600' : 'tw-text-green-600']">
          {{ service.variationPercentage >= 0 ? '+' : '' }}{{ (service.variationPercentage || 0).toFixed(1) }}%
        </div>
        <div class="tw-text-xs tw-text-gray-600">
          {{ service.variationValue >= 0 ? '+' : '' }}${{ (service.variationValue || 0).toFixed(2) }}
        </div>
      </div>
    </div>
    
    <!-- Mostrar mais se houver mais dados -->
    <div v-if="serviceVariationData.length > 5" class="tw-text-center tw-pt-2">
      <span class="tw-text-xs tw-text-gray-500">
        +{{ serviceVariationData.length - 5 }} serviços adicionais
      </span>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      serviceVariationData: []
    }
  }
}
</script>
