<?php
// view.php - Affichage d'une note markdown unique

if (!isset($file_path) || !file_exists($file_path)) {
    echo "<p class='error'>Fichier non trouvable</p>";
    exit;
}

// Lire et parser le fichier markdown
$content = file_get_contents($file_path);
$folder_base = dirname($file_path);
$html = parseMarkdownToHtml($content, $folder_base);
echo $html;

/**
 * Diviser une ligne de tableau sur | en respectant les délimiteurs [[ ]]
 */
function splitTableCells($line) {
    $line = trim($line, '|');
    $cells = [];
    $current = '';
    $bracket_depth = 0;

    for ($i = 0; $i < strlen($line); $i++) {
        $char = $line[$i];

        // Tracker les crochets [[ ]]
        if ($char === '[' && $i + 1 < strlen($line) && $line[$i + 1] === '[') {
            $bracket_depth++;
            $current .= $char;
        } elseif ($char === ']' && $i + 1 < strlen($line) && $line[$i + 1] === ']') {
            $bracket_depth--;
            $current .= $char;
        } elseif ($char === '|' && $bracket_depth === 0) {
            // Division sur | seulement si pas dans [[ ]]
            $cells[] = trim($current);
            $current = '';
        } else {
            $current .= $char;
        }
    }

    if (!empty($current)) {
        $cells[] = trim($current);
    }

    return $cells;
}

/**
 * Chercher un fichier par son nom (avec ou sans .md)
 */
function findFileByName($name, $base_path) {
    $files = scandir($base_path, SCANDIR_SORT_NONE);
    foreach ($files as $file) {
        if ($file === '.' || $file === '..') continue;

        $full_path = $base_path . '/' . $file;
        if (is_file($full_path) && preg_match('/\.md$/', $file)) {
            if (str_replace('.md', '', $file) === $name || $file === $name) {
                return $full_path;
            }
        } elseif (is_dir($full_path)) {
            $result = findFileByName($name, $full_path);
            if ($result) return $result;
        }
    }
    return null;
}

/**
 * Trouver la racine du projet en remontant jusqu'au dossier contenant .images/
 */
function findProjectRoot($base_path) {
    $current = $base_path;
    while (true) {
        if (is_dir($current . '/.images')) {
            return $current;
        }
        $parent = dirname($current);
        if ($parent === $current) break;
        $current = $parent;
    }
    return $base_path;
}

/**
 * Chercher une image dans le dossier .images/ (invisible, à la racine du vault)
 */
function findImage($image_name, $base_path) {
    // Remonter jusqu'à la racine du vault (celui qui contient .images)
    $current = $base_path;

    // Chercher le dossier .images en remontant les répertoires
    while (strlen($current) > 1) {
        $images_path = $current . '/.images';
        if (is_dir($images_path)) {
            // Chercher le fichier exact
            $full_path = $images_path . '/' . $image_name;
            if (file_exists($full_path)) {
                return $full_path;
            }

            // Chercher en ignorant la casse
            $files = scandir($images_path);
            foreach ($files as $file) {
                if (strtolower($file) === strtolower($image_name)) {
                    return $images_path . '/' . $file;
                }
            }

            // Dossier trouvé mais image pas dedans - retourner null
            return null;
        }
        $current = dirname($current);
    }

    return null;
}

/**
 * Générer un carrousel d'images (litegal)
 */
function generateCarousel($image_names, $base_path) {
    if (empty($image_names)) {
        return '';
    }

    $image_paths = [];
    foreach ($image_names as $img_name) {
        $img_path = findImage($img_name, $base_path);
        if ($img_path) {
            $relative_path = preg_replace('#^\./+#', '', $img_path);
            $image_paths[] = [
                'name' => htmlspecialchars($img_name),
                'path' => htmlspecialchars($relative_path)
            ];
        }
    }

    // Afficher le carrousel si au moins une image a été trouvée
    if (count($image_paths) > 0) {
        $carousel_id = 'carousel-' . uniqid();
        $html = '<div class="carousel" id="' . $carousel_id . '">';

        // Image principale
        $html .= '<div class="carousel-main">';
        $html .= '<img class="carousel-img" src="' . $image_paths[0]['path'] . '" alt="' . $image_paths[0]['name'] . '">';
        $html .= '</div>';

        // Vignettes
        $html .= '<div class="carousel-thumbs">';
        foreach ($image_paths as $idx => $img) {
            $active_class = ($idx === 0) ? ' active' : '';
            $html .= '<img class="carousel-thumb' . $active_class . '" src="' . $img['path'] . '" alt="' . $img['name'] . '" onclick="showCarouselImage(\'' . $carousel_id . '\', ' . $idx . ')">';
        }
        $html .= '</div>';

        $html .= '</div>';

        // Script pour gérer le carrousel
        $html .= '<script>' . "\n";
        $html .= 'window.carousels = window.carousels || {};' . "\n";
        $html .= 'window.carousels["' . $carousel_id . '"] = { current: 0, total: ' . count($image_paths) . ', images: ' . json_encode($image_paths) . ' };' . "\n";
        $html .= '</script>';

        return $html;
    }

    // Fallback: si des images manquent, les afficher de manière normal
    $html = '';
    foreach ($image_names as $img_name) {
        $img_path = findImage($img_name, $base_path);
        if ($img_path) {
            $relative_path = preg_replace('#^\./+#', '', $img_path);
            $html .= '<img src="' . htmlspecialchars($relative_path) . '" alt="' . htmlspecialchars($img_name) . '" class="obsidian-image" style="max-width: 100%; margin: 12px 0;">';
        }
    }
    return $html;
}

/**
 * Convertir Markdown en HTML avec support Obsidian
 */
function parseMarkdownToHtml($markdown, $base_path) {
    $lines = explode("\n", $markdown);
    $html = '';
    $in_frontmatter = false;
    $in_code_block = false;
    $code_language = '';
    $code_content = '';
    $in_table = false;
    $in_list = false;
    $list_level = 0;
    $in_litegal = false;
    $litegal_images = [];

    foreach ($lines as $line) {
        // Frontmatter YAML ou séparateur horizontal
        if (preg_match('/^---\s*$/', $line)) {
            if (!$in_frontmatter && empty($html)) {
                $in_frontmatter = true;
            } else if ($in_frontmatter) {
                $in_frontmatter = false;
            } else {
                // C'est un séparateur au milieu du document
                $html .= '<hr>';
            }
            continue;
        }

        if ($in_frontmatter) continue;

        // Gestion du litegal (carrousel)
        // Détection: bloc débutant par ``` suivi du mot 'litegal'
        if (preg_match('/^\s*```\s*litegal\s*$/i', $line)) {
            if (!$in_code_block && !$in_litegal) {
                $in_litegal = true;
                $litegal_images = [];
            }
            continue;
        }

        // Code blocks normaux (tolérer un espace en début de ligne sur la fermeture)
        if (preg_match('/^\s*```(\w*)/', $line, $matches)) {
            if (!$in_code_block && !$in_litegal) {
                // Ouverture d'un code block normal
                $in_code_block = true;
                $code_language = $matches[1] ?? '';
                $code_content = '';
            } else if ($in_litegal) {
                // Fermeture d'un bloc litegal
                $in_litegal = false;
                $carousel_html = generateCarousel($litegal_images, $base_path);
                if (!empty($carousel_html)) {
                    $html .= $carousel_html;
                }
                $litegal_images = [];
            } else if ($in_code_block) {
                // Fermeture d'un code block normal
                $in_code_block = false;
                $html .= '<pre class="code-block"><code class="language-' . htmlspecialchars($code_language) . '">'
                    . htmlspecialchars($code_content) . '</code></pre>';
                $code_content = '';
            }
            continue;
        }

        // Contenu du bloc litegal
        if ($in_litegal) {
            if (preg_match('/!\[\[([^\]|]+)/', $line, $matches)) {
                // Nettoyer le nom : retirer l'alias Obsidian (ex: image.jpeg|300 → image.jpeg)
                $litegal_images[] = trim($matches[1]);
            }
            continue;
        }

        // Contenu du code block normal
        if ($in_code_block) {
            $code_content .= $line . "\n";
            continue;
        }

        // Tables
        if (preg_match('/\|/', $line)) {
            if (!$in_table) {
                $html .= '<table class="dataview-table">';
                $in_table = true;
            }

            $cells = splitTableCells($line);
            // Rendre même les lignes avec une seule colonne
            if (count($cells) >= 1) {
                $row_tag = (strpos($line, '---') !== false) ? 'th' : 'td';
                $html .= '<tr>';
                foreach ($cells as $cell) {
                    if (!empty($cell) && $cell !== '---' && strpos($cell, '---') === false) {
                        $cell_html = processInlineMarkdown($cell, $base_path);
                        $html .= "<$row_tag>$cell_html</$row_tag>";
                    }
                }
                $html .= '</tr>';
            }
            continue;
        } else if ($in_table) {
            $html .= '</table>';
            $in_table = false;
        }

        // Titres
        if (preg_match('/^(#{1,6})\s+(.+)$/', $line, $matches)) {
            $level = strlen($matches[1]);
            $title = processInlineMarkdown($matches[2], $base_path);
            $id = 'h-' . preg_replace('/[^a-z0-9-]/i', '-', strtolower($title));
            $html .= "<h$level id='$id' class='header-$level'>$title</h$level>";
            continue;
        }

        // Listes (y compris checkboxes convertis en icônes)
        $line_for_list = preg_replace('/\[x\]/i', '◉', $line);
        $line_for_list = preg_replace('/\[ \]/', '◎', $line_for_list);

        if (preg_match('/^(\s*)[-*+]\s+(.+)$/', $line_for_list, $matches)) {
            $indent = strlen($matches[1]) / 2;
            $content = processInlineMarkdown($matches[2], $base_path);

            if ($indent > $list_level) {
                for ($i = $list_level; $i < $indent; $i++) {
                    $html .= '<ul>';
                }
            } else if ($indent < $list_level) {
                for ($i = $list_level; $i > $indent; $i--) {
                    $html .= '</ul>';
                }
            }

            $list_level = $indent;
            $html .= "<li>$content</li>";
            continue;
        } else if ($in_list && !empty($line)) {
            $html .= '</ul>';
            $in_list = false;
            $list_level = 0;
        }

        // Paragraphes
        $line = trim($line);
        if (!empty($line)) {
            $line_html = processInlineMarkdown($line, $base_path);
            $html .= "<p>$line_html</p>";
        }
    }

    // Fermer les balises ouvertes
    if ($in_code_block) {
        $html .= '<pre class="code-block"><code>' . htmlspecialchars($code_content) . '</code></pre>';
    }
    if ($in_litegal) {
        // Bloc litegal non fermé - générer quand même le carrousel
        $carousel_html = generateCarousel($litegal_images, $base_path);
        if (!empty($carousel_html)) {
            $html .= $carousel_html;
        }
    }
    if ($in_table) {
        $html .= '</table>';
    }
    while ($list_level > 0) {
        $html .= '</ul>';
        $list_level--;
    }

    return $html;
}

/**
 * Traiter les éléments inline (images, liens, etc)
 */
function processInlineMarkdown($text, $base_path) {
    // Images wiki style: ![[image.png]] ou ![[image.png|300]] (300 = largeur en px)
    $text = preg_replace_callback('/!\[\[([^\]|]+)(?:\|(\d+))?\]\]/', function($matches) use ($base_path) {
        $image_name = trim($matches[1]);
        $width = isset($matches[2]) && $matches[2] !== '' ? (int)$matches[2] : null;
        $image_path = findImage($image_name, $base_path);

        if ($image_path) {
            $relative_path = preg_replace('#^\./+#', '', $image_path);
            $style = $width ? ' style="width:' . $width . 'px; max-width:100%;"' : '';
            return '<img src="' . htmlspecialchars($relative_path) . '" alt="' . htmlspecialchars($image_name) . '" class="obsidian-image"' . $style . '>';
        }
        return htmlspecialchars($matches[0]);
    }, $text);

    // Images markdown style: ![alt](path)
    $text = preg_replace_callback('/!\[([^\]]*)\]\(([^)]+)\)/', function($matches) use ($base_path) {
        $alt = $matches[1];
        $path = $matches[2];

        // Si le chemin est relatif, le chercher localement
        if (!preg_match('#^https?://#', $path)) {
            $full_path = realpath($base_path . '/' . $path);
            if ($full_path && file_exists($full_path)) {
                $relative_path = str_replace($base_path, '', $full_path);
                $relative_path = ltrim($relative_path, '/');
                $path = $relative_path;
            }
        }

        return '<img src="' . htmlspecialchars($path) . '" alt="' . htmlspecialchars($alt) . '" class="obsidian-image">';
    }, $text);

    // Tags
    $text = preg_replace_callback('/#(\w+)/', function($matches) {
        return '<span class="tag">#' . htmlspecialchars($matches[1]) . '</span>';
    }, $text);

    // Liens internes: [[link|display]] ou [[link]]
    $text = preg_replace_callback('/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/', function($matches) use ($base_path) {
        $link = $matches[1];
        $display = $matches[2] ?? $link;

        // Chercher le fichier correspondant
        $file_path = null;

        $project_root = findProjectRoot($base_path);

        // Si le lien contient un chemin (avec /), résoudre depuis la racine du projet
        // (comportement Obsidian : les chemins sont toujours relatifs à la racine du vault)
        if (strpos($link, '/') !== false) {
            $candidate_path = $project_root . '/' . $link . '.md';
            if (file_exists($candidate_path)) {
                $file_path = $candidate_path;
            } else {
                // Fallback : essayer depuis le dossier courant
                $candidate_path = $base_path . '/' . $link . '.md';
                if (file_exists($candidate_path)) {
                    $file_path = $candidate_path;
                }
            }
        } else {
            // Recherche par nom depuis la racine du projet (trouve les fichiers à tous les niveaux)
            $file_path = findFileByName($link, $project_root);
        }

        if ($file_path) {
            $folder = $_GET['folder'] ?? $_SESSION['current_folder'] ?? '';
            $project_root = $base_path;
            while (!empty($folder) && basename($project_root) !== $folder && dirname($project_root) !== $project_root) {
                $project_root = dirname($project_root);
            }
            if (empty($folder) || dirname($project_root) === $project_root) {
                $project_root = dirname($base_path);
            }

            $file_key = str_replace($project_root . '/', '', $file_path);
            $href = '?folder=' . urlencode($folder) . '&file=' . urlencode($file_key);
            return '<a class="internal-link" href="' . htmlspecialchars($href) . '">' . htmlspecialchars($display) . '</a>';
        }
        return '<span class="internal-link" style="color: #525262;">' . htmlspecialchars($display) . '</span>';
    }, $text);

    // Liens externes: [text](url)
    $text = preg_replace_callback('/\[([^\]]+)\]\(([^)]+)\)/', function($matches) {
        $display = $matches[1];
        $url = $matches[2];

        // Lien vers un fichier STL (.stl/ relatif généré par prepare_folder.py)
        if (preg_match('/\.stl$/i', $url)) {
            $stl_filename = basename(urldecode($url));
            $folder = $_GET['folder'] ?? '';
            $file_param = '.stl/' . $stl_filename;
            $tab_url = '?folder=' . urlencode($folder) . '&file=' . urlencode($file_param);
            return '<a class="stl-link external-link" href="' . htmlspecialchars($tab_url) . '" data-stl-file="' . htmlspecialchars($file_param) . '">'
                . htmlspecialchars($display)
                . '</a>';
        }

        if (preg_match('#^https?://#', $url)) {
            return '<a class="external-link" href="' . htmlspecialchars($url) . '" target="_blank">' . htmlspecialchars($display) . '</a>';
        }
        return '<a class="external-link" href="' . htmlspecialchars($url) . '">' . htmlspecialchars($display) . '</a>';
    }, $text);

    // Gras: **text**
    $text = preg_replace('/\*\*([^\*]+)\*\*/', '<strong>$1</strong>', $text);

    // Italique: *text* ou _text_
    $text = preg_replace('/(?<!\*)\*(?!\*)([^\*]+)\*(?!\*)/', '<em>$1</em>', $text);
    $text = preg_replace('/_([^_]+)_/', '<em>$1</em>', $text);

    // Strikethrough: ~~text~~
    $text = preg_replace('/~~([^~]+)~~/', '<del>$1</del>', $text);

    // Code inline: `code`
    $text = preg_replace('/`([^`]+)`/', '<code>$1</code>', $text);

    return $text;
}
?>
