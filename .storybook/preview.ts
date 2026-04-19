import type { Preview } from '@storybook/react-vite'
import '../frontend/src/index.css'

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: 'surface',
      values: [
        { name: 'surface', value: '#f8f9fa' },
        { name: 'dark', value: '#2b3437' },
      ],
    },
    controls: { matchers: { color: /(background|color)$/i, date: /Date$/ } },
  },
}

export default preview
