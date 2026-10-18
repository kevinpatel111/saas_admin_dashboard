/**
 * Dashboard Analytics and Chart Initializations
 */

document.addEventListener('DOMContentLoaded', () => {
  // Chart.js default styling
  Chart.defaults.font.family = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
  Chart.defaults.color = '#858796';

  // Read data from window.chartData (populated by dashboard template)
  const chartData = window.chartData || {};

  // 1. Monthly Activity Bar Chart
  const monthlyCanvas = document.getElementById('monthlyChart');
  if (monthlyCanvas) {
    const monthlyLabels = chartData.monthly?.labels || ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const monthlyValues = chartData.monthly?.values || [12, 19, 15, 27, 34, 42, 38, 55, 48, 62, 59, 75];

    new Chart(monthlyCanvas, {
      type: 'bar',
      data: {
        labels: monthlyLabels,
        datasets: [{
          label: 'User Activity & Transactions',
          data: monthlyValues,
          backgroundColor: '#4e73df',
          hoverBackgroundColor: '#2e59d9',
          borderColor: '#4e73df',
          borderRadius: 6,
          maxBarThickness: 32
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: '#1a1d23',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            padding: 12,
            cornerRadius: 8,
            displayColors: false
          }
        },
        scales: {
          x: {
            grid: {
              display: false,
              drawBorder: false
            },
            ticks: {
              maxTicksLimit: 12
            }
          },
          y: {
            grid: {
              color: '#eaecf4',
              drawBorder: false,
              borderDash: [2]
            },
            ticks: {
              maxTicksLimit: 5,
              padding: 10
            }
          }
        }
      }
    });
  }

  // 2. Product Distribution Doughnut Chart
  const distributionCanvas = document.getElementById('distributionChart');
  if (distributionCanvas) {
    const distLabels = chartData.distribution?.labels || ['Electronics', 'SaaS Subscriptions', 'Hardware', 'Services', 'Accessories'];
    const distValues = chartData.distribution?.values || [45, 25, 15, 10, 5];

    new Chart(distributionCanvas, {
      type: 'doughnut',
      data: {
        labels: distLabels,
        datasets: [{
          data: distValues,
          backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e', '#e74a3b', '#6f42c1', '#fd7e14'],
          hoverBackgroundColor: ['#2e59d9', '#17a673', '#2c9faf', '#dda20a', '#be2617', '#59339d', '#d9650b'],
          hoverBorderColor: '#ffffff',
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              boxWidth: 14,
              padding: 16,
              usePointStyle: true,
              pointStyle: 'circle'
            }
          },
          tooltip: {
            backgroundColor: '#1a1d23',
            titleColor: '#ffffff',
            bodyColor: '#ffffff',
            padding: 12,
            cornerRadius: 8
          }
        },
        cutout: '72%'
      }
    });
  }
});
