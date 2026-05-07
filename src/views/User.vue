<template>
    <div class="user-page">
      <h1>User Page</h1>
      <p>This is the user page content.</p>
    </div>
  </template>
  
  <script>
  export default {
    name: 'User',
    // 可以在这里添加组件逻辑
    setup() {
      // 组件逻辑
      return {}
    }
  }
  </script>
  
  <style scoped>
  .user-page {
    padding: 20px;
  }
  
  h1 {
    color: #333;
  }
  </style>