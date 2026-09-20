import type { Monaco } from '@monaco-editor/react';

export function registerMcdLanguage(monaco: Monaco) {
  if (monaco.languages.getLanguages().some((language) => language.id === 'mcd')) {
    return;
  }
  monaco.languages.register({ id: 'mcd' });
  monaco.languages.setMonarchTokensProvider('mcd', {
    keywords: ['cloud', 'app', 'network', 'subnet', 'compute', 'storage', 'firewall', 'var', 'depends_on', 'true', 'false'],
    tokenizer: {
      root: [
        [/\/\/.*$/, 'comment'],
        [/\/\*/, 'comment', '@comment'],
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, 'string', '@string'],
        [/\$\{[A-Za-z_][\w-]*\}/, 'variable'],
        [/[A-Za-z_][\w-]*/, { cases: { '@keywords': 'keyword', '@default': 'identifier' } }],
        [/\d+/, 'number'],
        [/[{}[\]=,;]/, 'delimiter']
      ],
      string: [
        [/[^\\"]+/, 'string'],
        [/\\./, 'string.escape'],
        [/"/, 'string', '@pop']
      ],
      comment: [
        [/[^/*]+/, 'comment'],
        [/\*\//, 'comment', '@pop'],
        [/[/*]/, 'comment']
      ]
    }
  });
}
