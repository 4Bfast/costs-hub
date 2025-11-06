<script setup>
import { computed } from 'vue';
import flatPickr from 'vue-flatpickr-component';
import 'flatpickr/dist/flatpickr.css';
import { Portuguese } from 'flatpickr/dist/l10n/pt.js';

// PrimeVue Components
import Dropdown from 'primevue/dropdown';
import InputNumber from 'primevue/inputnumber';
import Button from 'primevue/button';

// Props
const props = defineProps({
  accounts: {
    type: Array,
    default: () => []
  },
  selectedAccount: {
    type: Object,
    default: null
  },
  dateRange: {
    type: Array,
    default: () => []
  },
  selectedService: {
    type: String,
    default: null
  },
  minVariation: {
    type: Number,
    default: 1.0
  },
  resultLimit: {
    type: Number,
    default: 20
  },
  isLoading: {
    type: Boolean,
    default: false
  }
});

// Emits
const emit = defineEmits([
  'update:selectedAccount',
  'update:dateRange',
  'update:selectedService',
  'update:minVariation',
  'update:resultLimit',
  'refresh'
]);

// Configuração do date picker
const datePickerConfig = {
  mode: 'range',
  dateFormat: 'd/m/Y',
  locale: Portuguese,
  maxDate: new Date(),
  defaultDate: props.dateRange
};

// Lista de serviços AWS
const awsServices = [
  { label: 'Todos os Serviços', value: null },
  { label: 'Amazon EC2', value: 'EC2' },
  { label: 'Amazon S3', value: 'S3' },
  { label: 'Amazon RDS', value: 'RDS' },
  { label: 'Amazon Lambda', value: 'Lambda' },
  { label: 'Amazon CloudFront', value: 'CloudFront' },
  { label: 'Amazon EBS', value: 'EBS' },
  { label: 'Amazon VPC', value: 'VPC' },
  { label: 'Amazon Route 53', value: 'Route53' },
  { label: 'Amazon CloudWatch', value: 'CloudWatch' },
  { label: 'Amazon ELB', value: 'ELB' }
];

// Computed properties para v-model
const selectedAccountModel = computed({
  get: () => props.selectedAccount,
  set: (value) => emit('update:selectedAccount', value)
});

const dateRangeModel = computed({
  get: () => props.dateRange,
  set: (value) => emit('update:dateRange', value)
});

const selectedServiceModel = computed({
  get: () => props.selectedService,
  set: (value) => emit('update:selectedService', value)
});

const minVariationModel = computed({
  get: () => props.minVariation,
  set: (value) => emit('update:minVariation', value)
});

const resultLimitModel = computed({
  get: () => props.resultLimit,
  set: (value) => emit('update:resultLimit', value)
});

// Métodos
const handleRefresh = () => {
  emit('refresh');
};
</script>

<template>
  <div class="variation-filters">
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      <!-- Conta AWS -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-2">
          Conta AWS
        </label>
        <Dropdown
          v-model="selectedAccountModel"
          :options="accounts"
          optionLabel="account_name"
          placeholder="Selecione uma conta"
          class="w-full"
          :disabled="isLoading"
        />
      </div>

      <!-- Período -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-2">
          Período
        </label>
        <flat-pickr
          v-model="dateRangeModel"
          :config="datePickerConfig"
          class="p-inputtext p-component w-full"
          placeholder="Selecione o período"
          :disabled="isLoading"
        />
      </div>

      <!-- Serviço -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-2">
          Serviço AWS
        </label>
        <Dropdown
          v-model="selectedServiceModel"
          :options="awsServices"
          optionLabel="label"
          optionValue="value"
          placeholder="Todos os serviços"
          class="w-full"
          :disabled="isLoading"
        />
      </div>

      <!-- Variação Mínima -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-2">
          Variação Mínima (%)
        </label>
        <InputNumber
          v-model="minVariationModel"
          :min="0"
          :max="1000"
          :step="0.1"
          suffix="%"
          placeholder="1.0"
          class="w-full"
          :disabled="isLoading"
        />
      </div>

      <!-- Limite de Resultados -->
      <div class="flex flex-col">
        <label class="text-sm font-medium text-gray-700 mb-2">
          Limite de Resultados
        </label>
        <InputNumber
          v-model="resultLimitModel"
          :min="1"
          :max="100"
          placeholder="20"
          class="w-full"
          :disabled="isLoading"
        />
      </div>

      <!-- Ações -->
      <div class="flex flex-col justify-end">
        <Button
          @click="handleRefresh"
          label="Atualizar"
          icon="pi pi-refresh"
          :loading="isLoading"
          class="w-full"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Customização do flatpickr */
:deep(.flatpickr-input) {
  width: 100%;
}
</style>
