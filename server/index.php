<?php
session_set_cookie_params(['httponly' => true, 'samesite' => 'Lax', 'secure' => true]);
session_start();

$config_file = __DIR__ . '/config.json';
if (!file_exists($config_file)) {
    $config = ['folders' => []];
    file_put_contents($config_file, json_encode($config, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
} else {
    $config = json_decode(file_get_contents($config_file), true);
}

$folders = $config['folders'] ?? [];
$selected_folder = $_GET['folder'] ?? $_SESSION['current_folder'] ?? null;
$selected_file = $_GET['file'] ?? null;
$authenticated = isset($_SESSION['folders'][$selected_folder]);

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
    $client_ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    if (_is_rate_limited($client_ip)) {
        $error = "Trop de tentatives. Réessayez dans 24h.";
    } else {
        $password = $_POST['password'];
        $found_folder = null;

        foreach ($folders as $folder_name => $folder_info) {
            if (password_verify($password, $folder_info['password'])) {
                $found_folder = $folder_name;
                break;
            }
        }

        if ($found_folder) {
            _reset_fails($client_ip);
            $_SESSION['folders'][$found_folder] = true;
            $_SESSION['current_folder'] = $found_folder;
            header("Location: ?folder=" . urlencode($found_folder));
            exit;
        } else {
            _record_fail($client_ip);
            $error = "Mot de passe incorrect";
        }
    }
}

if (isset($_GET['logout'])) {
    unset($_SESSION['folders'][$selected_folder]);
    unset($_SESSION['current_folder']);
    // Tabs cleared on client side (sessionStorage is per-session anyway)
    header("Location: index.php");
    exit;
}

if (isset($_GET['action']) && $_GET['action'] === 'search' && $authenticated && $selected_folder) {
    header('Content-Type: application/json; charset=utf-8');
    $q = mb_strtolower(trim($_GET['q'] ?? ''));
    $out = [];
    if (mb_strlen($q) >= 2 && isset($folders[$selected_folder])) {
        $base = realpath($folders[$selected_folder]['path']);
        if ($base) {
            $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator($base, RecursiveDirectoryIterator::SKIP_DOTS));
            foreach ($it as $f) {
                if ($f->getExtension() !== 'md') continue;
                $fp   = $f->getPathname();
                $name = $f->getBasename('.md');
                $rel  = str_replace(['\\', '/'], '/', substr($fp, strlen($base) + 1));
                $name_match = mb_strpos(mb_strtolower($name), $q) !== false;
                $snippet = '';
                $content_match = false;
                $raw = file_get_contents($fp);
                // strip frontmatter
                $body = preg_replace('/^---.*?---\s*/s', '', $raw);
                $body_lower = mb_strtolower($body);
                $pos = mb_strpos($body_lower, $q);
                if ($pos !== false) {
                    $content_match = true;
                    $start = max(0, $pos - 35);
                    $chunk = mb_substr($body, $start, mb_strlen($q) + 90);
                    $chunk = preg_replace('/\s+/', ' ', strip_tags($chunk));
                    $snippet = ($start > 0 ? '…' : '') . trim($chunk) . '…';
                }
                if ($name_match || $content_match) {
                    $out[] = ['file_key' => $rel, 'name' => $name, 'snippet' => $snippet, 'name_match' => $name_match];
                    if (count($out) >= 12) break;
                }
            }
            usort($out, fn($a, $b) => $b['name_match'] - $a['name_match']);
        }
    }
    echo json_encode($out);
    exit;
}

function _get_fail_file(string $ip): string {
    $dir = sys_get_temp_dir() . '/obsidian_fails';
    if (!is_dir($dir)) mkdir($dir, 0700, true);
    return $dir . '/' . md5($ip) . '.json';
}

function _is_rate_limited(string $ip): bool {
    $file = _get_fail_file($ip);
    if (!file_exists($file)) return false;
    $data = json_decode(file_get_contents($file), true);
    if (!$data || (time() - ($data['since'] ?? 0)) > 86400) return false;
    return ($data['count'] ?? 0) >= 500;
}

function _record_fail(string $ip): void {
    $file = _get_fail_file($ip);
    $data = ['count' => 0, 'since' => time()];
    if (file_exists($file)) {
        $stored = json_decode(file_get_contents($file), true);
        if ($stored && (time() - ($stored['since'] ?? 0)) <= 86400) $data = $stored;
    }
    $data['count']++;
    file_put_contents($file, json_encode($data), LOCK_EX);
}

function _reset_fails(string $ip): void {
    $file = _get_fail_file($ip);
    if (file_exists($file)) unlink($file);
}

function scanFolderStructure($path) {
    $structure = [];
    if (!is_dir($path)) return $structure;

    $items = scandir($path);
    $dirs = [];
    $files = [];

    foreach ($items as $item) {
        if ($item === '.' || $item === '..' || $item === 'images' || $item[0] === '.') continue;

        $full_path = $path . '/' . $item;
        if (is_dir($full_path)) {
            $dirs[$item] = [
                'type' => 'dir',
                'children' => scanFolderStructure($full_path)
            ];
        } elseif (pathinfo($item, PATHINFO_EXTENSION) === 'md') {
            $files[$item] = [
                'type' => 'file',
                'path' => str_replace($path . '/', '', $full_path)
            ];
        }
    }

    ksort($dirs);
    ksort($files);
    $structure = array_merge($dirs, $files);

    return $structure;
}


?>
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Obsidian Share</title>
    <link rel="icon" href="./logo.png" type="image/png">
    <style>
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body, #root { height: 100%; overflow: hidden; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif; background: #1e1e1e; color: #dcddde; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

.layout { display: flex; height: 100vh; overflow: hidden; }

/* ── SIDEBAR ─────────────────────────────────────────────────── */
.sidebar {
  background: #262626; display: flex; flex-direction: column;
  overflow: hidden; flex-shrink: 0; position: relative;
  border-right: 1px solid #252525;
}
.sidebar-header { padding: 16px 14px 10px; flex-shrink: 0; }
.vault-title { display: flex; align-items: center; gap: 7px; margin-bottom: 12px; justify-content: space-between; }
.vault-logo { width: 18px; height: 18px; object-fit: contain; flex-shrink: 0; }
.vault-name { font-size: 14px; font-weight: 600; color: #e0e0e0; letter-spacing: -0.01em; }
.vault-sub  { font-size: 14px; font-weight: 200; color: #e0e0e0; letter-spacing: -0.01em; }

.search-bar {
  display: flex; align-items: center; gap: 7px;
  background: rgba(255,255,255,0.05); border-radius: 5px;
  padding: 5px 9px; cursor: text;
}
.search-bar svg { color: #4a4a4a; flex-shrink: 0; }
.search-input-sidebar {
  flex: 1; background: transparent; border: none; outline: none;
  font-size: 12px; color: #d0d0d0; min-width: 0;
}
.search-input-sidebar::placeholder { color: #4a4a4a; }
.search-clear {
  width: 14px; height: 14px; border-radius: 50%; background: rgba(255,255,255,0.15);
  color: #aaa; font-size: 9px; display: none; align-items: center; justify-content: center;
  cursor: pointer; flex-shrink: 0; line-height: 1;
}
.search-clear:hover { background: rgba(255,255,255,0.25); color: #fff; }
.search-results-wrap { position: relative; }
.search-results {
  display: none; position: absolute; top: 4px; left: 0; right: 0; z-index: 200;
  background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 6px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5); max-height: 340px; overflow-y: auto;
}
.search-result-item {
  padding: 8px 12px; cursor: pointer; border-bottom: 1px solid rgba(255,255,255,0.05);
  transition: background 0.1s;
}
.search-result-item:last-child { border-bottom: none; }
.search-result-item:hover { background: rgba(255,255,255,0.06); }
.search-result-name { font-size: 12.5px; color: #e0e0e0; font-weight: 500; }
.search-result-snippet { font-size: 11px; color: #6a6a6a; margin-top: 2px; line-height: 1.4; }
.search-highlight { background: rgba(167,139,250,0.3); color: #c4b5fd; border-radius: 2px; padding: 0 1px; }
.search-no-results { padding: 12px; font-size: 12px; color: #555; text-align: center; }
.search-mode .tree-row.search-hidden { display: none; }
.search-mode .tree-children { display: block !important; }
.search-mode .tree-children.search-hidden-folder { display: none !important; }

.sidebar-tree { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 4px 0 24px; }

/* ── TREE ────────────────────────────────────────────────────── */
.tree-row {
  display: flex; align-items: center; height: 24px;
  cursor: pointer; border-radius: 4px; margin: 0 5px;
  padding-right: 6px; white-space: nowrap; overflow: hidden;
  transition: background 0.1s, color 0.1s;
}
.tree-row:hover { background: rgba(255,255,255,0.07); }
.tree-row.active { background: rgba(124,58,237,0.22); }
.tree-row.active:hover { background: rgba(124,58,237,0.3); }

.ti {
  flex-shrink: 0; width: 18px; height: 24px;
  position: relative;
}
.ti-line {
  position: absolute; left: 9px; top: 0; bottom: 0;
  width: 1px; background: rgba(255,255,255,0.09);
}
.tree-children {
  position: relative; margin-left: 0;
  display: none;  /* Fermés par défaut */
}
.tree-children[data-depth="1"]::before { left: 19px; }
.tree-children[data-depth="2"]::before { left: 37px; }
.tree-children[data-depth="3"]::before { left: 55px; }
.tree-children[data-depth="4"]::before { left: 73px; }
.tree-children[data-depth="5"]::before { left: 91px; }
.tree-children[data-depth="6"]::before { left: 109px; }
.tree-children[data-depth="7"]::before { left: 127px; }
.tree-children[data-depth="8"]::before { left: 145px; }
.tree-children::before {
  content: '';
  position: absolute;
  top: 0; bottom: 0;
  width: 1px;
  background: rgba(255,255,255,0.2);
  pointer-events: none;
}

.tree-arrow {
  width: 14px; height: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  color: #555; font-size: 8px; transition: transform 0.15s;
}
.tree-arrow.open { transform: rotate(90deg); }
.tree-arrow.hidden { opacity: 0; pointer-events: none; }

.tree-label {
  flex: 1; font-size: 12.5px; overflow: hidden; text-overflow: ellipsis;
  color: #e8e2f5; line-height: 24px; padding-left: 3px;
}
.tree-row:hover .tree-label { color: #f0ebf8; }
.tree-row.active .tree-label { color: #ffffff; }
.tree-row.file .tree-label { color: #a8a8a8; }
.tree-row.file:hover .tree-label { color: #d8d8d8; }
.tree-row.file.active .tree-label { color: #ececec; }

.resize-handle {
  position: absolute; right: 0; top: 0; bottom: 0; width: 4px;
  cursor: col-resize; z-index: 10; transition: background 0.15s;
}
.resize-handle:hover { background: rgba(124,58,237,0.5); }

/* ── MAIN COLUMN ─────────────────────────────────────────────── */
.main-col { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; background: #1e1e1e; }

/* ── TABBAR ──────────────────────────────────────────────────── */
.tabbar {
  height: 36px; flex-shrink: 0;
  background: #363636; border-bottom: 1px solid #252525;
  display: flex; align-items: center; padding: 0 6px; gap: 1px; overflow: visible;
}
.tabs-row { display: flex; align-items: center; gap: 1px; min-width: 0; }

.tab {
  display: flex; align-items: center; width: 220px;
  height: 27px; padding: 0 8px 0 12px; margin-right: 4px;
  background: #262626; border: none; border-radius: 6px 6px 6px 6px;
  color: #aaaaaa; cursor: pointer;
  font-size: 12px; font-family: inherit; flex-shrink: 0;
  transition: color 0.1s, background 0.1s;
}
.tab:hover { color: #9783e1; background: #262626; }
.tab.active { color: #e0e0e0; background: #1e1e1e; margin-bottom: -11px; height: auto; min-height: 38px; padding-bottom: 11px; align-self: flex-end; }
.tab-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
.tab-close {
  width: 14px; height: 14px; border: none; background: transparent;
  color: inherit; cursor: pointer; display: flex; align-items: center;
  justify-content: center; border-radius: 3px; opacity: 0;
  font-size: 11px; flex-shrink: 0; transition: opacity 0.1s, background 0.1s;
}
.tab:hover .tab-close, .tab.active .tab-close { opacity: 0.5; }
.tab-close:hover { opacity: 1 !important; background: rgba(255,255,255,0.14); }

.tab-add {
  width: 24px; height: 24px; border: none; background: transparent;
  color: #989898; cursor: pointer; border-radius: 4px; flex-shrink: 0;
  font-size: 16px; display: flex; align-items: center; justify-content: center;
  transition: color 0.1s, background 0.1s; margin-left: 2px;
}
.tab-add:hover { color: #c0c0c0; background: rgba(255,255,255,0.07); }

/* ── CONTENT ─────────────────────────────────────────────────── */
.content-outer { flex: 1; overflow: hidden; display: flex; flex-direction: column; position: relative; }

.nav-arrows {
  position: absolute; top: 14px; left: 22px; z-index: 20;
  display: flex; gap: 2px; pointer-events: none;
}
.nav-btn {
  width: 22px; height: 22px; border: none; background: transparent;
  color: #7e7e7e; cursor: pointer; display: flex; align-items: center;
  justify-content: center; border-radius: 4px; pointer-events: all;
  transition: color 0.12s, background 0.12s;
}
.nav-btn:hover:not(:disabled) { color: #aaaaaa; background: rgba(255,255,255,0.07); }
.nav-btn:disabled { opacity: 0.4; cursor: default; }

.content-scroll { flex: 1; overflow-y: scroll; overflow-x: hidden; }
.content-scroll::-webkit-scrollbar { width: 6px; }
.content-scroll::-webkit-scrollbar-track { background: #1e1e1e; }
.content-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.09); border-radius: 3px; }
.content-scroll::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.18); }

.content-inner { max-width: 820px; width: 100%; padding: 52px 68px 80px 40px; margin: 0 auto; }

/* Viewer STL — remplit toute la zone de contenu */
.content-scroll.stl-view { overflow: hidden; display: flex; flex-direction: column; }
.content-inner.stl-view { max-width: none; padding: 0; margin: 0; flex: 1 1 0; display: flex; flex-direction: column; min-height: 0; }
.stl-iframe { flex: 1 1 0; min-height: 0; width: 100%; border: none; display: block; }

.breadcrumb { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; font-size: 11px; color: #3e3e3e; margin-bottom: 24px; }
.bc-sep { color: #2e2e2e; }
.bc-item { cursor: pointer; transition: color 0.12s; }
.bc-item:hover { color: #777; }
.bc-item.last { color: #5a5a5a; cursor: default; }

/* ── MARKDOWN ────────────────────────────────────────────────── */
.md h1 { font-size: 25px; font-weight: 700; color: #e8e8e8; margin: 32px 0 26px; line-height: 1.25; }
.md h2 { font-size: 16px; font-weight: 600; color: #dedede; margin: 32px 0 28px; padding-bottom: 6px; border-bottom: 1px solid #272727; }
.md h3 { font-size: 14px; font-weight: 600; color: #d0d0d0; margin: 20px 0 24px; }
.md p { font-size: 13.5px; line-height: 1.75; color: #b0b1b3; margin-bottom: 12px; }
.md ul, .md ol { padding-left: 20px; margin-bottom: 12px; }
.md li { font-size: 13.5px; line-height: 1.75; color: #b0b1b3; margin-bottom: 3px; }
.md code { background: rgba(255,255,255,0.07); border-radius: 3px; padding: 1px 5px; font-size: 12px; font-family: 'SF Mono','Fira Code',Consolas,monospace; color: #9d7fe8; }
.md pre { background: rgba(0,0,0,0.3); border-radius: 6px; padding: 14px; margin-bottom: 16px; overflow-x: auto; }
.md pre code { background: transparent; padding: 0; color: #c8c9cb; }
.md blockquote { border-left: 3px solid #6d3aed; padding: 2px 0 2px 14px; margin: 14px 0; }
.md blockquote p { color: #6e6e7e; font-style: italic; margin: 0; }
.md hr { border: none; border-top: 2px solid #3a3a3a; margin: 26px 0; }
.md a { color: #9d7fe8; text-decoration: none; cursor: pointer; }
.md a:hover { text-decoration: underline; }
.md strong { color: #e0e0e0; font-weight: 600; }
.md em { font-style: italic; color: #c0c0c0; }
.md del { text-decoration: line-through; color: #666666; }
.md table { border-collapse: collapse; width: 100%; margin: 12px 0; }
.md table th, .md table td { border: 1px solid #272727; padding: 8px; text-align: left; }
.md table th { background: rgba(255,255,255,0.05); }
.md img { max-width: 100%; border-radius: 4px; }

/* ── EMPTY STATE ─────────────────────────────────────────────── */
.empty-state { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14px; height: 100%; }
.empty-state svg { opacity: 0.18; }
.empty-state p { font-size: 13px; color: #808080; }

/* ── TOC ─────────────────────────────────────────────────────── */
.toc-trigger { position: fixed; right: 0; top: 36px; bottom: 0; width: 41px; z-index: 48; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='35' height='210'%3E%3Crect x='1' y='10' width='28' height='3' rx='1.5' fill='%23c0c0c0' fill-opacity='0.25'/%3E%3Crect x='6' y='34' width='21' height='2' rx='1' fill='%23c0c0c0' fill-opacity='0.18'/%3E%3Crect x='10' y='57' width='15' height='2' rx='1' fill='%23c0c0c0' fill-opacity='0.13'/%3E%3Crect x='1' y='80' width='28' height='3' rx='1.5' fill='%23c0c0c0' fill-opacity='0.25'/%3E%3Crect x='6' y='104' width='21' height='2' rx='1' fill='%23c0c0c0' fill-opacity='0.18'/%3E%3Crect x='10' y='127' width='15' height='2' rx='1' fill='%23c0c0c0' fill-opacity='0.13'/%3E%3Crect x='1' y='150' width='28' height='3' rx='1.5' fill='%23c0c0c0' fill-opacity='0.25'/%3E%3Crect x='6' y='174' width='21' height='2' rx='1' fill='%23c0c0c0' fill-opacity='0.18'/%3E%3Crect x='10' y='197' width='15' height='2' rx='1' fill='%23c0c0c0' fill-opacity='0.13'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 6px center; background-size: 35px 210px; }
.toc-panel {
  position: fixed; right: 0; top: 36px; bottom: 0;
  width: 210px; background: #1e1e1e; border-left: 0px solid #252525;
  padding: 35px 0; overflow-y: auto; z-index: 49;
  transform: translateX(100%); transition: transform 0.18s ease; pointer-events: none;
}
.toc-panel.open { transform: translateX(0); pointer-events: all; }
.toc-head { font-size: 10px; font-weight: 600; color: #f8f8f8; text-transform: uppercase; letter-spacing: 0.08em; padding: 0 16px 10px; }
.toc-link { display: block; font-size: 12px; color: #B2B2B2; padding: 3px 16px; cursor: pointer; border-left: 2px solid transparent; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; transition: color 0.1s, background 0.1s; line-height: 1.65; }
.toc-link:hover { color: #c0c0c0; background: rgba(255,255,255,0.04); }
.toc-link.active { color: #a78bfa; border-left-color: #7c3aed; }
.toc-link.h2 { padding-left: 24px; }
.toc-link.h3 { padding-left: 32px; font-size: 11px; }

/* ── HOME LOGIN ──────────────────────────────────────────────── */
.home-container {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  height: 100vh; background: #1e1e1e;
}
.home-header {
  display: none;
}
.logo-section { display: flex; align-items: center; gap: 16px; }
.logo { width: 48px; height: 48px; }
.logo-text { display: flex; flex-direction: column; gap: 0; }
.logo-title { font-size: 16px; font-weight: 600; color: #e0e0e0; }
.logo-subtitle { font-size: 12px; font-weight: 200; color: #a0a0a0; }

.home-search {
  display: flex; flex-direction: column; gap: 32px; align-items: center;
}
.password-form-wrapper {
  display: flex; flex-direction: column; gap: 32px; align-items: center; width: 100%;
}
.search-input {
  width: 320px; padding: 12px 16px; background: #333333;
  border: none; border-radius: 40px; color: #dcddde;
  font-size: 14px; outline: none;
}
.search-input::placeholder { color: #4a4a4a; }
.search-input:focus { background: #3a3a3a; outline: none; box-shadow: none; }
.password-submit {
  display: none;
}

.error-message {
  color: #d05450; font-size: 13px; margin-top: 12px;
}

/* ── INTERNAL LINKS ──────────────────────────────────────── */
.internal-link {
    text-decoration: none !important;
    border-bottom: none !important;
    color: #e3e3e3 !important;
    box-shadow: 0 0 0 1px #7f6df2 !important;
    border: none !important;
    border-radius: 4px !important;
    padding: 1px 5px !important;
    margin: 0px 2px !important;
    background-color: transparent !important;
    transition: all 0.15s ease-in-out;
    cursor: pointer;
}

.internal-link:hover {
    color: #7f6df2 !important;
    background-color: rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 0 0 1px transparent !important;
    text-decoration: none !important;
    border-bottom: none !important;
}

/* ── LIENS EXTERNES ──────────────────────────────────────── */
.external-link {
    color: #e3e3e3 !important;
    text-decoration: none !important;
    border-bottom: 1px solid rgba(244, 242, 255, 0.25) !important;
    padding-bottom: 0.5px !important;
    transition: all 0.2s ease-in-out;
    cursor: pointer;
}

.external-link:hover {
    color: #a594f9 !important;
    border-bottom: 1px solid rgba(165, 148, 249, 0.6) !important;
    text-decoration: none !important;
}

/* ── CARROUSEL ──────────────────────────────────────────────── */
.carousel {
    position: relative;
    background: #0a0a0a;
    border: 1px solid #252525;
    border-radius: 8px;
    overflow: hidden;
    margin: 16px 0;
}

.carousel-main {
    width: 100%;
    aspect-ratio: 16 / 10;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #161616;
}

.carousel-img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}

.carousel-thumbs {
    display: flex;
    gap: 8px;
    padding: 8px;
    background: #262626;
    overflow-x: auto;
}

.carousel-thumb {
    width: 70px;
    height: 70px;
    object-fit: cover;
    border-radius: 4px;
    cursor: pointer;
    border: 2px solid transparent;
    transition: all 0.2s;
    opacity: 0.6;
    flex-shrink: 0;
}

.carousel-thumb:hover {
    opacity: 0.8;
}

.carousel-thumb.active {
    border-color: #7f6df2;
    opacity: 1;
}

.carousel-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0, 0, 0, 0.6);
    color: #e0e0e0;
    border: none;
    padding: 8px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 18px;
    z-index: 10;
    transition: all 0.2s;
}

.carousel-btn:hover {
    background: rgba(127, 109, 242, 0.3);
    color: #7f6df2;
}

.carousel-prev {
    left: 12px;
}

.carousel-next {
    right: 12px;
}

/* ── HAMBURGER MENU ──────────────────────────────────── */
.hamburger-btn {
    background: transparent;
    border: none;
    color: #888;
    cursor: pointer;
    font-size: 20px;
    padding: 4px 0px 4px 6px;
    transition: all 0.3s;
    flex-shrink: 0;
    margin-left: auto;
    margin-right: 0px;
    align-self: center;
    margin-top: -17px;
}

.hamburger-btn:hover {
    color: #ddd;
}

.hamburger-fixed {
    position: fixed;
    left: 5px;
    top: 0px;
    background: transparent;
    border: none;
    color: #888;
    cursor: pointer;
    font-size: 20px;
    padding: 4px 6px;
    z-index: 40;
    transition: all 0.3s;
    display: none;
}

.hamburger-fixed:hover {
    color: #ddd;
}

.sidebar.hidden {
    display: none;
}

.layout.sidebar-hidden .hamburger-fixed {
    display: block;
}

.layout.sidebar-hidden .tabbar {
    padding-left: 40px;
}

.layout.sidebar-hidden .content-outer {
    margin-left: 0;
}
    </style>
</head>
<body>
    <div id="root">
        <?php if ($authenticated && $selected_folder): ?>
            <!-- HAMBURGER FIXE (de secours, visible quand sidebar cachée) -->
            <button class="hamburger-fixed" id="hamburger-fixed" onclick="toggleSidebar()" style="display: none;">☰</button>

            <div class="layout">
                <!-- SIDEBAR -->
                <div class="sidebar" id="sidebar" style="width: 248px;">
                    <div class="sidebar-header">
                        <div class="vault-title">
                            <img class="vault-logo" src="./logo.png" alt="Obsidian">
                            <span class="vault-name">Obsidian</span>
                            <span class="vault-sub">Share</span>
                            <button class="hamburger-btn" id="hamburger" onclick="toggleSidebar()">☰</button>
                        </div>
                        <div class="search-bar" id="search-wrap">
                            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                <circle cx="5" cy="5" r="3.5" stroke="currentColor" stroke-width="1.2"/>
                                <path d="M8 8L10.5 10.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
                            </svg>
                            <input type="text" id="search-input" class="search-input-sidebar" placeholder="Rechercher…" autocomplete="off" spellcheck="false">
                            <div id="search-clear" class="search-clear">✕</div>
                        </div>
                        <div class="search-results-wrap">
                            <div id="search-results" class="search-results"></div>
                        </div>
                    </div>

                    <nav class="sidebar-tree" id="tree">
                        <?php
                        $folder_path = $folders[$selected_folder]['path'];
                        $structure = scanFolderStructure($folder_path);

                        function renderTree($items, $depth = 0, $path = '', $selected_file = '') {
                            $count = count($items);
                            $idx = 0;
                            foreach ($items as $name => $item) {
                                $idx++;
                                $item_path = $path ? $path . '/' . $name : $name;

                                if ($item['type'] === 'dir') {
                                    echo '<div class="tree-row" onclick="toggleFolder(event, \'' . htmlspecialchars(addslashes($name)) . '\')" data-folder="' . htmlspecialchars($name) . '">';
                                    for ($i = 0; $i < $depth; $i++) {
                                        echo '<div class="ti"></div>';
                                    }
                                    echo '<span class="tree-arrow">›</span>';
                                    echo '<span class="tree-label">' . htmlspecialchars($name) . '</span>';
                                    echo '</div>';
                                    echo '<div class="tree-children" style="display:none;" data-folder="' . htmlspecialchars($name) . '" data-depth="' . ($depth + 1) . '">';
                                    renderTree($item['children'], $depth + 1, $item_path, $selected_file);
                                    echo '</div>';
                                } else {
                                    $is_active = ($item_path === $selected_file) ? ' active' : '';
                                    echo '<div class="tree-row file' . $is_active . '" onclick="openFile(\'' . htmlspecialchars(addslashes($item_path)) . '\')">';
                                    for ($i = 0; $i < $depth; $i++) {
                                        echo '<div class="ti"></div>';
                                    }
                                    echo '<span class="tree-arrow hidden">›</span>';
                                    echo '<span class="tree-label">' . htmlspecialchars(str_replace('.md', '', $name)) . '</span>';
                                    echo '</div>';
                                }
                            }
                        }

                        renderTree($structure, 0, '', $selected_file, []);
                        ?>
                    </nav>

                    <div style="padding: 12px 18px; border-top: 1px solid #757575;">
                        <a href="?logout=1" style="color: #ffffff; text-decoration: none; font-size: 12px;">Déconnexion</a>
                    </div>

                    <div class="resize-handle" id="resizeHandle"></div>
                </div>

                <!-- MAIN COLUMN -->
                <div class="main-col">
                    <!-- TABBAR -->
                    <div class="tabbar">
                        <div class="tabs-row" id="tabs-row"></div>
                    </div>

                    <!-- CONTENT -->
                    <div class="content-outer">
                        <div class="nav-arrows">
                            <button class="nav-btn" id="nav-back" onclick="goBack()" disabled>
                                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                    <path d="M7.5 2L3 6L7.5 10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </button>
                            <button class="nav-btn" id="nav-forward" onclick="goForward()" disabled>
                                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                                    <path d="M4.5 2L9 6L4.5 10" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>
                                </svg>
                            </button>
                        </div>

                        <?php $is_stl_view = $selected_file && pathinfo($selected_file, PATHINFO_EXTENSION) === 'stl'; ?>
                        <div class="content-scroll<?= $is_stl_view ? ' stl-view' : '' ?>" id="content-scroll">
                            <div class="content-inner<?= $is_stl_view ? ' stl-view' : '' ?>" id="content-inner">
                                <?php if ($selected_file): ?>
                                    <?php
                                    // Validation sécurité via realpath (anti path-traversal)
                                    $base_dir = realpath($folders[$selected_folder]['path']);
                                    $file_path_abs = $base_dir ? realpath($base_dir . '/' . $selected_file) : false;
                                    if (!$file_path_abs || !$base_dir || strpos($file_path_abs, $base_dir . DIRECTORY_SEPARATOR) !== 0) {
                                        $file_path = null;
                                    } else {
                                        // Chemin relatif original : nécessaire pour view.php (calcul URLs images/carousel)
                                        $file_path = $folders[$selected_folder]['path'] . '/' . $selected_file;
                                    }
                                    if ($is_stl_view) {
                                        // Affichage du viewer 3D dans un onglet du site
                                        $stl_file = basename($selected_file);
                                        $viewer_src = 'viewer.php?folder=' . urlencode($selected_folder) . '&file=' . urlencode($stl_file) . '&embed=1';
                                        echo '<iframe src="' . htmlspecialchars($viewer_src) . '" class="stl-iframe" allowfullscreen></iframe>';
                                    } elseif ($file_path && file_exists($file_path) && pathinfo($file_path, PATHINFO_EXTENSION) === 'md') {
                                        $file_title = str_replace('.md', '', basename($selected_file));
                                        echo '<h1>' . htmlspecialchars($file_title) . '</h1>';
                                        echo '<div id="note-content" class="md" style="margin-top: 20px">';
                                        include 'view.php';
                                        echo '</div>';
                                    } else {
                                        echo '<div class="empty-state"><p>📄 Fichier non trouvé</p></div>';
                                    }
                                    ?>
                                <?php else: ?>
                                    <div class="empty-state">
                                        <svg width="38" height="38" viewBox="0 0 38 38" fill="none">
                                            <rect x="5" y="3" width="28" height="33" rx="3" stroke="#888" stroke-width="1.5"/>
                                            <path d="M11 13h16M11 18h16M11 23h10" stroke="#888" stroke-width="1.5" stroke-linecap="round"/>
                                        </svg>
                                        <p>Sélectionnez une note pour commencer</p>
                                    </div>
                                <?php endif; ?>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- TOC PANEL -->
                <div class="toc-trigger" id="toc-trigger" onmouseenter="showTOC()" onmouseleave="hideTOC()"></div>
                <div class="toc-panel" id="toc-panel" onmouseenter="showTOC()" onmouseleave="hideTOC()">
                    <div class="toc-head">Structure</div>
                    <div id="toc-links"></div>
                </div>
            </div>

        <?php else: ?>
            <!-- LOGIN HOME -->
            <div class="home-container">
                <form method="POST" class="password-form-wrapper">
                    <div class="logo-section">
                        <img src="./logo.png" alt="Obsidian" class="logo">
                        <div style="font-size: 36px; color: #e8e8e8;"><span style="font-weight: 700;">Obsidian</span> <span style="font-weight: 300;">Share</span></div>
                    </div>
                    <input
                        type="password"
                        name="password"
                        placeholder="Votre mot de passe…"
                        class="search-input"
                        autofocus
                    >
                    <?php if (isset($error)): ?>
                        <div class="error-message"><?php echo htmlspecialchars($error); ?></div>
                    <?php endif; ?>
                </form>
            </div>
        <?php endif; ?>
    </div>

    <script>
let tocTimer = null;
let sidebarWidth = 248;

class TabManager {
    constructor(folder) {
        this.folder = folder;
        this.nextTabId = 1;
        this.restoreTabs();
    }

    restoreTabs() {
        const key = 'tabs_' + this.folder;
        const stored = sessionStorage.getItem(key);
        if (stored) {
            const data = JSON.parse(stored);
            this.tabs = data.tabs || [];
            this.activeTabId = data.activeTabId || null;
            this.nextTabId = data.nextTabId || 1;
        } else {
            this.tabs = [];
            this.activeTabId = null;
            this.nextTabId = 1;
        }
    }

    saveTabs() {
        const key = 'tabs_' + this.folder;
        sessionStorage.setItem(key, JSON.stringify({
            tabs: this.tabs,
            activeTabId: this.activeTabId,
            nextTabId: this.nextTabId
        }));
    }

    createNewTab() {
        const tabId = 'tab-' + (this.nextTabId++);
        const tab = {
            id: tabId,
            file: null,
            label: 'Nouvelle note',
            history: [],
            histIdx: -1,
            visible: false
        };
        this.tabs.push(tab);
        this.activeTabId = tabId;
        this.saveTabs();
        return tab;
    }

    setTabFile(tabId, file) {
        const tab = this.tabs.find(t => t.id === tabId);
        if (!tab) return;

        tab.file = file;
        tab.label = file.split('/').pop().replace(/\.(md|stl)$/i, '');
        tab.visible = true;

        if (tab.history[tab.histIdx] !== file) {
            tab.history = tab.history.slice(0, tab.histIdx + 1);
            tab.history.push(file);
            tab.histIdx++;
        }

        this.activeTabId = tabId;
        this.saveTabs();
    }

    closeTab(tabId) {
        const idx = this.tabs.findIndex(t => t.id === tabId);
        const wasActive = this.activeTabId === tabId;

        if (idx > -1) {
            this.tabs.splice(idx, 1);
        }

        if (wasActive) {
            // Priorité : onglet visible à gauche, sinon à droite
            const visibleBefore = this.tabs.slice(0, idx).filter(t => t.visible);
            const visibleAfter  = this.tabs.slice(idx).filter(t => t.visible);
            const next = visibleBefore[visibleBefore.length - 1] || visibleAfter[0] || null;
            this.activeTabId = next ? next.id : null;
        }

        this.saveTabs();
    }

    activateTab(tabId) {
        this.activeTabId = tabId;
        this.saveTabs();
    }

    getActiveTab() {
        return this.tabs.find(t => t.id === this.activeTabId);
    }

    goBack() {
        const tab = this.getActiveTab();
        if (!tab || tab.histIdx <= 0) return null;
        tab.histIdx--;
        this.saveTabs();
        return tab.history[tab.histIdx];
    }

    goForward() {
        const tab = this.getActiveTab();
        if (!tab || tab.histIdx >= tab.history.length - 1) return null;
        tab.histIdx++;
        this.saveTabs();
        return tab.history[tab.histIdx];
    }

    canGoBack() {
        const tab = this.getActiveTab();
        return tab && tab.histIdx > 0;
    }

    canGoForward() {
        const tab = this.getActiveTab();
        return tab && tab.histIdx < tab.history.length - 1;
    }
}

let tabManager;

document.addEventListener('DOMContentLoaded', function() {
    const folder = new URLSearchParams(window.location.search).get('folder');
    const file = new URLSearchParams(window.location.search).get('file');
    tabManager = new TabManager(folder);

    // If there's a file in the URL, load it into a tab
    if (file) {
        let activeTab = tabManager.getActiveTab();
        if (!activeTab) {
            // Create first tab if none exists
            activeTab = tabManager.createNewTab();
        }
        tabManager.setTabFile(activeTab.id, file);
    }

    extractTOC();
    setupScrollSpy();
    setupSidebarResize();
    setupFolderToggle();
    loadFolderState();
    renderTabs();
    updateNavButtons();
    initSearch();
});

function initSearch() {
    const input   = document.getElementById('search-input');
    const results = document.getElementById('search-results');
    const clearBtn = document.getElementById('search-clear');
    if (!input) return;

    let debounce = null;
    let current  = '';

    input.addEventListener('input', () => {
        const q = input.value.trim();
        current = q;
        clearBtn.style.display = q ? 'flex' : 'none';
        if (q.length < 2) { closeResults(); resetTreeFilter(); return; }
        filterTree(q);
        clearTimeout(debounce);
        debounce = setTimeout(() => searchContent(q), 300);
    });

    clearBtn.addEventListener('click', () => {
        input.value = ''; current = '';
        clearBtn.style.display = 'none';
        closeResults(); resetTreeFilter(); input.focus();
    });

    input.addEventListener('keydown', e => {
        if (e.key === 'Escape') { input.value = ''; current = ''; clearBtn.style.display = 'none'; closeResults(); resetTreeFilter(); }
    });

    document.addEventListener('click', e => {
        if (!e.target.closest('#search-wrap') && !e.target.closest('.search-results-wrap')) closeResults();
    });

    function filterTree(q) {
        const tree = document.getElementById('tree');
        if (!tree) return;
        tree.classList.add('search-mode');
        const ql = q.toLowerCase();

        // Étape 1 : filtrer uniquement les fichiers par nom
        tree.querySelectorAll('.tree-row.file').forEach(row => {
            const label = row.querySelector('.tree-label');
            row.classList.toggle('search-hidden', !(label && label.textContent.toLowerCase().includes(ql)));
        });

        // Étape 2 : afficher les dossiers parents des fichiers qui matchent,
        // cacher les dossiers sans aucun fichier matching dans leur sous-arbre.
        // On cherche uniquement des fichiers (.tree-row.file) pour ne jamais
        // filtrer sur le nom des dossiers.
        const containers = Array.from(tree.querySelectorAll('.tree-children'));
        containers.sort((a, b) => parseInt(b.dataset.depth || 0) - parseInt(a.dataset.depth || 0));
        containers.forEach(container => {
            const hasMatch = !!container.querySelector('.tree-row.file:not(.search-hidden)');
            container.classList.toggle('search-hidden-folder', !hasMatch);
            const folderRow = container.previousElementSibling;
            if (folderRow && folderRow.classList.contains('tree-row') && !folderRow.classList.contains('file')) {
                folderRow.classList.toggle('search-hidden', !hasMatch);
            }
        });
    }

    function resetTreeFilter() {
        const tree = document.getElementById('tree');
        if (!tree) return;
        tree.classList.remove('search-mode');
        tree.querySelectorAll('.search-hidden').forEach(el => el.classList.remove('search-hidden'));
        tree.querySelectorAll('.search-hidden-folder').forEach(el => el.classList.remove('search-hidden-folder'));
    }

    function searchContent(q) {
        if (q !== current) return;
        const folder = tabManager?.folder || new URLSearchParams(window.location.search).get('folder');
        if (!folder) return;
        fetch(`?action=search&folder=${encodeURIComponent(folder)}&q=${encodeURIComponent(q)}`)
            .then(r => r.json())
            .then(data => { if (q === current) showResults(data, q); })
            .catch(() => {});
    }

    function showResults(data, q) {
        results.innerHTML = '';
        if (!data.length) {
            results.innerHTML = '<div class="search-no-results">Aucun résultat</div>';
            results.style.display = 'block'; return;
        }
        data.forEach(item => {
            const div = document.createElement('div');
            div.className = 'search-result-item';
            div.innerHTML = `<div class="search-result-name">${hl(htmlEscape(item.name), q)}</div>` +
                (item.snippet ? `<div class="search-result-snippet">${hl(htmlEscape(item.snippet), q)}</div>` : '');
            div.addEventListener('click', () => {
                const folder = tabManager?.folder || new URLSearchParams(window.location.search).get('folder');
                window.location.href = `?folder=${encodeURIComponent(folder)}&file=${encodeURIComponent(item.file_key)}`;
            });
            results.appendChild(div);
        });
        results.style.display = 'block';
    }

    function closeResults() { if (results) results.style.display = 'none'; }

    function hl(text, q) {
        const esc = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return text.replace(new RegExp(`(${esc})`, 'gi'), '<mark class="search-highlight">$1</mark>');
    }
}

function updateNavButtons() {
    const backBtn = document.getElementById('nav-back');
    const forwardBtn = document.getElementById('nav-forward');
    const tab = tabManager.getActiveTab();

    if (backBtn) {
        backBtn.disabled = !tabManager.canGoBack();
    }
    if (forwardBtn) {
        forwardBtn.disabled = !tabManager.canGoForward();
    }
}

function openFile(fileKey) {
    const activeTab = tabManager.getActiveTab();
    if (!activeTab) {
        // No active tab, create one
        const newTab = tabManager.createNewTab();
        tabManager.setTabFile(newTab.id, fileKey);
    } else {
        tabManager.setTabFile(activeTab.id, fileKey);
    }
    window.location.href = '?folder=' + encodeURIComponent(tabManager.folder) + '&file=' + encodeURIComponent(fileKey);
}

function toggleFolder(event, folderName) {
    const row = event.target.closest('.tree-row');
    if (!row) return;
    const children = row.nextElementSibling;
    const arrow = row.querySelector('.tree-arrow');
    if (children && children.classList.contains('tree-children')) {
        if (children.style.display === 'none') {
            children.style.display = 'block';
            arrow.classList.add('open');
            saveFolderState(folderName, true);
        } else {
            children.style.display = 'none';
            arrow.classList.remove('open');
            saveFolderState(folderName, false);
        }
    }
}

function saveFolderState(folderName, isOpen) {
    const state = JSON.parse(localStorage.getItem('folderState') || '{}');
    state[folderName] = isOpen;
    localStorage.setItem('folderState', JSON.stringify(state));
}

function loadFolderState() {
    const state = JSON.parse(localStorage.getItem('folderState') || '{}');
    const folder = new URLSearchParams(window.location.search).get('folder');

    document.querySelectorAll('.tree-row[data-folder]').forEach(row => {
        const folderName = row.getAttribute('data-folder');
        const children = row.nextElementSibling;
        const arrow = row.querySelector('.tree-arrow');

        if (state[folderName]) {
            children.style.display = 'block';
            arrow.classList.add('open');
        } else {
            children.style.display = 'none';
            arrow.classList.remove('open');
        }
    });
}

function setupFolderToggle() {
    document.querySelectorAll('.tree-row').forEach(row => {
        const children = row.nextElementSibling;
        if (children && children.classList.contains('tree-children') && children.children.length > 0) {
            row.style.cursor = 'pointer';
        }
    });
}

function extractTOC() {
    const content = document.getElementById('note-content');
    const tocPanel = document.getElementById('toc-panel');
    if (!content || !tocPanel) return;

    const headings = content.querySelectorAll('h1, h2, h3');
    const toc = document.getElementById('toc-links');

    if (headings.length === 0) {
        tocPanel.style.display = 'none';
        return;
    }

    tocPanel.style.display = 'block';
    toc.innerHTML = '';
    headings.forEach((h, i) => {
        const id = h.id || 'heading-' + i;
        h.id = id;

        const link = document.createElement('div');
        const levelClass = h.tagName === 'H3' ? ' h3' : h.tagName === 'H2' ? ' h2' : '';
        link.className = 'toc-link' + levelClass;
        link.textContent = h.textContent;
        link.onclick = () => {
            h.scrollIntoView({ behavior: 'smooth' });
            const scroll = document.getElementById('content-scroll');
            if (scroll) scroll.scrollTop = h.offsetTop - 56;
        };
        toc.appendChild(link);
    });
}

function setupScrollSpy() {
    const scroll = document.getElementById('content-scroll');
    if (!scroll) return;

    scroll.addEventListener('scroll', () => {
        const headings = document.querySelectorAll('#note-content h1, #note-content h2, #note-content h3');
        let active = null;

        headings.forEach(h => {
            const rect = h.getBoundingClientRect();
            if (rect.top <= 100) active = h.id;
        });

        document.querySelectorAll('.toc-link').forEach(link => link.classList.remove('active'));
        if (active) {
            const idx = Array.from(headings).findIndex(h => h.id === active);
            const links = document.querySelectorAll('.toc-link');
            if (links[idx]) links[idx].classList.add('active');
        }
    });
}

function setupSidebarResize() {
    const handle = document.getElementById('resizeHandle');
    const sidebar = document.getElementById('sidebar');
    let isResizing = false;
    let startX = 0;

    handle.addEventListener('mousedown', e => {
        isResizing = true;
        startX = e.clientX;
        e.preventDefault();
    });

    document.addEventListener('mousemove', e => {
        if (!isResizing) return;
        const delta = e.clientX - startX;
        const newWidth = Math.max(180, Math.min(500, sidebarWidth + delta));
        sidebar.style.width = newWidth + 'px';
        sidebarWidth = newWidth;
    });

    document.addEventListener('mouseup', () => {
        isResizing = false;
    });
}

function showTOC() {
    clearTimeout(tocTimer);
    const panel = document.getElementById('toc-panel');
    if (panel) panel.classList.add('open');
}

function hideTOC() {
    tocTimer = setTimeout(() => {
        const panel = document.getElementById('toc-panel');
        if (panel) panel.classList.remove('open');
    }, 280);
}

function renderTabs() {
    const tabsRow = document.getElementById('tabs-row');

    // Remove existing tabs but keep the add button
    Array.from(tabsRow.children).forEach(child => {
        if (!child.classList.contains('tab-add')) {
            child.remove();
        }
    });

    // Only render visible tabs
    const visibleTabs = tabManager.tabs.filter(t => t.visible);
    visibleTabs.forEach(tab => {
        const tabEl = document.createElement('div');
        tabEl.className = 'tab' + (tab.id === tabManager.activeTabId ? ' active' : '');
        tabEl.dataset.tabId = tab.id;
        tabEl.innerHTML = `<span class="tab-label">${htmlEscape(tab.label)}</span><button class="tab-close" onclick="closeTabEl(event)">×</button>`;
        tabEl.onclick = () => switchTab(tab.id);
        tabsRow.appendChild(tabEl);
    });

    // Ensure add button exists in tabs-row
    if (!tabsRow.querySelector('.tab-add')) {
        const addBtn = document.createElement('button');
        addBtn.className = 'tab-add';
        addBtn.textContent = '+';
        addBtn.onclick = addTab;
        tabsRow.appendChild(addBtn);
    }
}

function htmlEscape(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function addTab() {
    const newTab = tabManager.createNewTab();
    renderTabs();
    // Show empty state since new tab has no file
    window.location.href = '?folder=' + encodeURIComponent(tabManager.folder);
}

// Ouvrir un fichier STL dans un nouvel onglet du site
document.addEventListener('click', function(e) {
    const link = e.target.closest('.stl-link[data-stl-file]');
    if (!link || !tabManager) return;
    e.preventDefault();
    const fileParam = link.getAttribute('data-stl-file');
    const newTab = tabManager.createNewTab();
    tabManager.setTabFile(newTab.id, fileParam);
    renderTabs();
    window.location.href = '?folder=' + encodeURIComponent(tabManager.folder) + '&file=' + encodeURIComponent(fileParam);
});

function closeTabEl(e) {
    e.stopPropagation();
    const tab = e.target.closest('.tab');
    if (!tab) return;
    const tabId = tab.dataset.tabId;
    const closingTab = tabManager.tabs.find(t => t.id === tabId);

    tabManager.closeTab(tabId);
    renderTabs();
    updateNavButtons();

    const activeTab = tabManager.getActiveTab();
    if (!activeTab) {
        // No more tabs, return to empty state
        window.location.href = '?folder=' + encodeURIComponent(tabManager.folder);
    } else if (activeTab.file) {
        window.location.href = '?folder=' + encodeURIComponent(tabManager.folder) + '&file=' + encodeURIComponent(activeTab.file);
    }
}

function switchTab(tabId) {
    const tab = tabManager.tabs.find(t => t.id === tabId);
    if (!tab) return;
    tabManager.activateTab(tabId);
    renderTabs();
    updateNavButtons();

    if (tab.file) {
        window.location.href = '?folder=' + encodeURIComponent(tabManager.folder) + '&file=' + encodeURIComponent(tab.file);
    } else {
        window.location.href = '?folder=' + encodeURIComponent(tabManager.folder);
    }
}

function goBack() {
    const file = tabManager.goBack();
    if (!file) return;
    updateNavButtons();
    window.location.href = '?folder=' + encodeURIComponent(tabManager.folder) + '&file=' + encodeURIComponent(file);
}

function goForward() {
    const file = tabManager.goForward();
    if (!file) return;
    updateNavButtons();
    window.location.href = '?folder=' + encodeURIComponent(tabManager.folder) + '&file=' + encodeURIComponent(file);
}
    </script>

    <!-- Carrousel JavaScript -->
    <script>
    function showCarouselImage(carouselId, index) {
        if (!window.carousels || !window.carousels[carouselId]) return;

        const carousel = window.carousels[carouselId];
        carousel.current = index % carousel.total;

        const mainImg = document.querySelector('#' + carouselId + ' .carousel-img');
        if (mainImg) {
            mainImg.src = carousel.images[carousel.current].path;
            mainImg.alt = carousel.images[carousel.current].name;
        }

        // Mettre à jour les vignettes
        document.querySelectorAll('#' + carouselId + ' .carousel-thumb').forEach((thumb, idx) => {
            thumb.classList.toggle('active', idx === carousel.current);
        });
    }

    function carouselPrev(carouselId) {
        if (!window.carousels || !window.carousels[carouselId]) return;
        const carousel = window.carousels[carouselId];
        let prev = carousel.current - 1;
        if (prev < 0) prev = carousel.total - 1;
        showCarouselImage(carouselId, prev);
    }

    function carouselNext(carouselId) {
        if (!window.carousels || !window.carousels[carouselId]) return;
        const carousel = window.carousels[carouselId];
        const next = (carousel.current + 1) % carousel.total;
        showCarouselImage(carouselId, next);
    }

    // Hamburger menu toggle
    function toggleSidebar() {
        const sidebar = document.getElementById('sidebar');
        const hamburger = document.getElementById('hamburger');
        const hamburgerFixed = document.getElementById('hamburger-fixed');
        const layout = document.querySelector('.layout');

        sidebar.classList.toggle('hidden');
        hamburger.classList.toggle('sidebar-hidden');
        layout.classList.toggle('sidebar-hidden');

        // Montrer/cacher le hamburger fixe
        const isHidden = sidebar.classList.contains('hidden');
        hamburgerFixed.style.display = isHidden ? 'block' : 'none';

        // Sauvegarder l'état dans sessionStorage
        sessionStorage.setItem('sidebarHidden', isHidden);
    }

    // Restaurer l'état au chargement
    window.addEventListener('DOMContentLoaded', function() {
        const hamburgerFixed = document.getElementById('hamburger-fixed');
        if (sessionStorage.getItem('sidebarHidden') === 'true') {
            toggleSidebar();
        }
    });
    </script>
</body>
</html>
