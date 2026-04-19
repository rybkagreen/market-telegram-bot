import { useEffect } from 'react'

interface IconSpriteLoaderProps {
  url?: string
}

/**
 * Fetches the SVG sprite once and injects it into <body>,
 * so every <use href="#rh-foo"/> resolves locally without
 * repeat network round-trips. Mount once inside PortalShell.
 */
export function IconSpriteLoader({ url = '/icons/rh-sprite.svg' }: IconSpriteLoaderProps) {
  useEffect(() => {
    if (document.getElementById('__rh-icon-sprite')) return
    let cancelled = false
    fetch(url)
      .then((r) => r.text())
      .then((svg) => {
        if (cancelled) return
        if (document.getElementById('__rh-icon-sprite')) return
        const wrap = document.createElement('div')
        wrap.id = '__rh-icon-sprite'
        wrap.style.display = 'none'
        wrap.setAttribute('aria-hidden', 'true')
        wrap.innerHTML = svg
        document.body.appendChild(wrap)
        window.__RH_ICON_SPRITE = ''
      })
      .catch((err) => {
        console.error('[IconSpriteLoader] failed to load sprite:', err)
      })
    return () => {
      cancelled = true
    }
  }, [url])
  return null
}
