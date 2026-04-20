import fs from 'node:fs'
import path from 'node:path'
import type { Plugin } from 'vite'

interface InlineSpriteOptions {
  spritePath: string
}

/**
 * Injects the icon sprite directly into index.html at build time, with
 * its styling co-located inside the SVG itself.
 *
 * Why the <style> block goes inside the sprite:
 *   <use href="#rh-foo"/> creates a shadow tree for the referenced
 *   symbol. Selectors from the outer document's stylesheet (e.g.
 *   ".rh-icon .rh-stroke") only cross the shadow boundary by
 *   implementation-specific behavior — Chrome/Firefox apply them,
 *   iOS Safari does not, which leaves the icons invisible on iPhone
 *   (no fill/stroke). A <style> element *inside* the sprite applies
 *   to the sprite's own tree and travels with the shadow content, so
 *   icons render reliably on every engine including iOS Safari.
 */
const SPRITE_STYLE = `<style>
  .rh-stroke { fill: none; stroke: currentColor; stroke-width: var(--rh-stroke-w, 1.5); stroke-linecap: round; stroke-linejoin: round; }
  .rh-fill   { fill: currentColor; }
</style>`

export function inlineSprite({ spritePath }: InlineSpriteOptions): Plugin {
  const absolute = path.resolve(spritePath)

  function readAndDecorate(): string {
    const raw = fs.readFileSync(absolute, 'utf-8')
    const stripped = raw.replace(/<\?xml[^?]*\?>\s*/i, '').trim()
    // Inject the style block just inside <defs>. Works for empty or
    // populated <defs>. If the sprite ever ships without <defs>, fall
    // back to injecting right after the opening <svg ...> tag.
    if (/<defs[^>]*>/i.test(stripped)) {
      return stripped.replace(/<defs([^>]*)>/i, `<defs$1>${SPRITE_STYLE}`)
    }
    return stripped.replace(/(<svg[^>]*>)/i, `$1<defs>${SPRITE_STYLE}</defs>`)
  }

  return {
    name: 'rh-inline-sprite',
    transformIndexHtml: {
      order: 'pre',
      handler(html) {
        const svg = readAndDecorate()
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
