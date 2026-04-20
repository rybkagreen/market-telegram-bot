import fs from 'node:fs'
import path from 'node:path'
import type { Plugin } from 'vite'

interface InlineSpriteOptions {
  spritePath: string
}

export function inlineSprite({ spritePath }: InlineSpriteOptions): Plugin {
  const absolute = path.resolve(spritePath)

  return {
    name: 'rh-inline-sprite',
    transformIndexHtml: {
      order: 'pre',
      handler(html) {
        const raw = fs.readFileSync(absolute, 'utf-8')
        const svg = raw.replace(/<\?xml[^?]*\?>\s*/i, '').trim()
        return html.replace(/(<body[^>]*>)/i, `$1\n    ${svg}`)
      },
    },
    configureServer(server) {
      server.watcher.add(absolute)
      server.watcher.on('change', (file) => {
        if (path.resolve(file) === absolute) {
          server.ws.send({ type: 'full-reload' })
        }
      })
    },
  }
}
