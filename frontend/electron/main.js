const { app, BrowserWindow, globalShortcut, Tray, Menu, nativeImage } = require('electron')
const path = require('path')

let mainWindow
let tray

const isDev = process.env.NODE_ENV !== 'production'

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
        frame: true,
        titleBarStyle: 'hiddenInset',
        backgroundColor: '#0a0a0f',
        show: false,
    })

    // Load the app
    if (isDev) {
        mainWindow.loadURL('http://localhost:3000')
        mainWindow.webContents.openDevTools()
    } else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
    }

    // Show window when ready
    mainWindow.once('ready-to-show', () => {
        mainWindow.show()
    })

    // Handle window close - hide instead of quit
    mainWindow.on('close', (event) => {
        if (!app.isQuitting) {
            event.preventDefault()
            mainWindow.hide()
        }
    })
}

function createTray() {
    // Create a simple tray icon
    const icon = nativeImage.createFromDataURL(
        'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsMAAA7DAcdvqGQAAAGPSURBVFhH7ZY9TsNAEIV3vQ5/ESVFJDoKKpAbcAPIHbgBF6CgpoGWhoKSKj0NBRIFEhUXIIWQEgQRJBjPy6wVr9drO8RKiEjzpK/YmXk7s7O2NzQ0NPQ/kSQ3SvlqcbkoaY8BHyQpR0l6YyJzGxXRziEu0/Cp0Tp9GDy2SPOzMSfYSJIX/GLAK0n3rNfrp6AO6vVKDXUPiEgfGHCfpBcWaWRVN4BVarXaEfCAcxBTsNx8gY0HtPkH15mFuKYWwBnSGHaAdQB8E+YCiB3gNeBz4Pu+J7QfhnEHYC8O9A6cBmF/A7ALXjh3wDuC4D6AO8E74GvCXHAFeEnwZ0J7AXgeXAE+Al4K8/lCGMPXhH0C+xqw28F1wjzwEqh0EvhNmK8D+wb2deAL4Bzw0ngIeBJ4K+w94DPge+Az4DPgc+BL4HPgC+BL4EvgS+BL4MuA'
    )

    tray = new Tray(icon)

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Show Ira',
            click: () => mainWindow.show()
        },
        { type: 'separator' },
        {
            label: 'Quit',
            click: () => {
                app.isQuitting = true
                app.quit()
            }
        }
    ])

    tray.setToolTip('Ira - AI Assistant')
    tray.setContextMenu(contextMenu)

    // Show window on tray double-click
    tray.on('double-click', () => {
        mainWindow.show()
    })
}

function registerShortcuts() {
    // Global hotkey to toggle window (Ctrl+Space)
    globalShortcut.register('CommandOrControl+Space', () => {
        if (mainWindow.isVisible()) {
            mainWindow.hide()
        } else {
            mainWindow.show()
            mainWindow.focus()
        }
    })
}

app.whenReady().then(() => {
    createWindow()
    createTray()
    registerShortcuts()

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow()
        }
    })
})

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('will-quit', () => {
    globalShortcut.unregisterAll()
})
