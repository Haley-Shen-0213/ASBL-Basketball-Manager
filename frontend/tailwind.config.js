/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 背景色系
        'asbl-bg': '#0b1220',      // 網頁深色底
        'asbl-panel': '#C084FC',   // 側邊欄底色 (舊版變數)
        'asbl-main': '#BFA8FF',    // 主內容區底色 (舊版變數)
        
        // 漸層色系 (Header)
        'asbl-pink': '#FFA6C9',
        'asbl-blue': '#21B7D6',
        'asbl-violet': '#8B5CF6',

        // 金色字體 (Brand)
        'gold-light': '#FFFFFF',
        'gold-main': '#F8E3B0',
        'gold-shadow': '#A67C00',
      },
      backgroundImage: {
        'header-gradient': 'linear-gradient(90deg, #FFA6C9 0%, #FFAACD 12%, #7ED3E3 22%, #21B7D6 35%, #1FB0D0 55%, #5DA9EF 65%, #7F6AF6 78%, #8B5CF6 100%)',
        'gold-text': 'linear-gradient(180deg, #FFFFFF 0%, #F8E3B0 55%, #A67C00 100%)',
      }
    },
  },
  plugins: [],
}
