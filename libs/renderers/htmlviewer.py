from contextlib import contextmanager
from libs.optlib import optrecord
from pathlib import Path
from collections import defaultdict
import html
import json
import sys

class HtmlDoc:
    def __init__(self) -> None:
        self.html_output = '<!DOCTYPE html>\n'
        self.level = 0
        self.tag_stack = []

    def __str__(self):
        return self.html_output

    def __indent(self):
        # Use 2 spaces for indentation.
        return ('  ')*self.level

    def __enter_tag(self, name, attributes):
        self.html_output += self.__indent() + '<' + name
        for a in attributes:
            self.html_output += ' ' + a + '=\"' + \
                html.escape(attributes[a]) + "\""

        self.html_output += '>\n'
        self.level += 1

    def __exit_tag(self, name):
        self.level -= 1
        self.html_output += self.__indent() + '</' + name + '>\n'

    def __append(self, content):
        content = str(content)
        # Split the lines and indent.
        for line in content.split('\n'):
            # Output only non-empty lines.
            if line:
                self.html_output += self.__indent() + line + '\n'

    @contextmanager
    def tag(self, name, attributes={}):
        self.__enter_tag(name, attributes)
        yield
        self.__exit_tag(name)

    def itag(self, name, content, attributes={}):
        self.__enter_tag(name, attributes)
        self.__append(content)
        self.__exit_tag(name)
        while self.tag_stack:
            nested_tag = self.tag_stack.pop()
            self.__exit_tag(nested_tag)
        return self

    def ntag(self, name, attributes={}):
        self.__enter_tag(name, attributes)
        self.tag_stack.append(name)
        return self

    def insert(self, content):
        self.__append(content)

def generate_head(editor):
    with editor.tag('head'):
        editor.insert('''
            <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
            <style type="text/css">
            html,
            body {
                width: 100%;
                height: 100%;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }
            .RemarkInlineDecoration {
                background-color: yellow;
                cursor: pointer;
            }
            .side-pane {
                background: rgba(200, 200, 200, .2);
                width: 20%;
                height: 100%;
                float: left;
            }
            .editor-pane {
                width: 80%;
                height: 100%;
                float: right;
            }
            .file:hover {
                background: yellow;
                cursor: pointer;
            }
            </style>'''
        )

def generate_decorations(file, file_remarks):
    # Process remarks to create decorations in the source.
    remarks = file_remarks[Path(file).name]
    decorations_list = []
    line_col_remarks = defaultdict(list)
    for lineno in sorted(remarks):
        if lineno == 0:
            continue
        for rr in sorted(remarks[lineno], key=lambda e: (e.Line, e.Column)):
            if isinstance(rr, optrecord.Passed):
                kind = 'Passed'
                continue
            elif isinstance(rr, optrecord.Missed):
                kind = 'Missed'
            else:  # analysis
                kind = 'Analysis'
                # TODO: handle analysis remarks.
                continue
            if rr.Column == 0:
                print('Warning: column 0', sys._getframe())
            line_col_remarks[(rr.Line, rr.Column)].append(
                (kind, rr.message))
    for line, col in line_col_remarks:
        values = []
        for r in line_col_remarks[(line, col)]:
            kind = r[0]
            message = r[1]
            values.append(
                #{'value': '%s [Run command](command:${cmdId})' % ('**' + kind + '**\\\n' + message ), 'supportHtml' : 'true', 'isTrusted':'true'})
                {'value': '%s' % ('**' + kind + '**\\\n' + message ), 'supportHtml' : 'true'})
        decorations_list.append(
            {
                'lineNumber': '%s'%(line),
                'Column': '%s'%(col),
                'hoverMessage': values,
                'inlineClassName': '%s'%('RemarkInlineDecoration')
            }
        )

    decorations_json = json.dumps(decorations_list)
    return decorations_json

def generate_sidepane(editor, fileinfo_list):
    with editor.tag('div', { 'class' : 'side-pane'}):
        with editor.tag('ul'):
            for fileinfo in fileinfo_list:
                file = fileinfo['file']
                file_remarks = fileinfo['file_remarks']
                decorations_json = generate_decorations(file, file_remarks)
                with open(file, 'r') as f:
                    source = f.read()
                # TODO: Update tree view to show directory structure.
                filename = Path(file).name
                editor.itag(
                    'li', filename, {
                        'class': 'file',
                        'data-uri': '%s' % (file),
                        'data-source': '%s' % (source),
                        'data-decorations': '%s' % (decorations_json)
                    }
                )

def render_html(fileinfo_list):
    editor = HtmlDoc()
    with editor.tag('html'):
        generate_head(editor)
        with editor.tag('body'):
            generate_sidepane(editor, fileinfo_list)
            editor.itag('div', '', {'id': 'container', 'class': 'editor-pane'})
            editor.insert('<script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs/loader.min.js" integrity="sha512-6bIYsGqvLpAiEBXPdRQeFf5cueeBECtAKJjIHer3BhBZNTV3WLcLA8Tm3pDfxUwTMIS+kAZwTUvJ1IrMdX8C5w==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>')
            with editor.tag('script'):
                editorContainer = r'''
                    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.34.1/min/vs' } });
                    require(['vs/editor/editor.main'], function () {
                        var editor = monaco.editor.create(document.getElementById('container'), {
                            value: '[Click on file]',
                            readOnly: true,
                            renderValidationDecorations: 'on',
                            minimap: {
                                scale: 1
                            },
                        });

                        const cmdId = editor.addCommand(0, () => {
                            alert("Test command!")
                        }, "")

                        console.log(cmdId)

                        function createDecorations(decorationJson) {
                            decorations = []
                            model = editor.getModel()
                            for (var r of decorationJson) {
                                lineNumber = parseInt(r.lineNumber)
                                Column = parseInt(r.Column)
                                position = { lineNumber: lineNumber, column: Column }
                                word = model.getWordAtPosition(position)
                                if (word == null) {
                                    startColumn = position.column;
                                    endColumn = startColumn + 1;
                                    range = new monaco.Range(lineNumber, startColumn, lineNumber, endColumn)
                                    char = model.getValueInRange(range)
                                    // Highlight the whole line for a pragma.
                                    if (char == '#')
                                        endColumn = model.getLineMaxColumn(position.lineNumber)
                                }
                                else {
                                    startColumn = word.startColumn
                                    endColumn = word.endColumn
                                }

                                decoration = {
                                    range: new monaco.Range(lineNumber, startColumn, lineNumber, endColumn),
                                    options: {
                                        hoverMessage: r.hoverMessage,
                                        inlineClassName: r.inlineClassName,
                                        minimap: {
                                            color: 'yellow',
                                            darkColor: 'yellow',
                                            position: monaco.editor.MinimapPosition.Inline
                                        }
                                    }
                                }

                                decorations.push(decoration)
                            }

                            return decorations
                        }

                        var viewstates = {}
                        function updateEditorModel() {
                            const files = document.getElementsByClassName('file')
                            for(i=0; i<files.length; ++i) {
                                files[i].addEventListener('click', event => {
                                        const models = monaco.editor.getModels()
                                        const uri = monaco.Uri.file(event.target.dataset.uri)

                                        // Save viewstate, to restore if the file is loaded again.
                                        const prev_model = editor.getModel()
                                        if (prev_model)
                                            viewstates[prev_model.uri] = editor.saveViewState()

                                        var model = monaco.editor.getModel(uri)
                                        if (!model) {
                                            //console.log('Create model', uri)
                                            model = monaco.editor.createModel(
                                                event.target.dataset.source, /* value */
                                                undefined, /* language */
                                                uri /* uri */
                                            );
                                            //console.log(model.getLanguageId())
                                        }

                                        decorationsJson = JSON.parse(event.target.dataset.decorations)
                                        editor.setModel(model)
                                        decorations = createDecorations(decorationsJson)
                                        editor.createDecorationsCollection(decorations)
                                        viewstate = viewstates[uri]
                                        if (viewstate)
                                            editor.restoreViewState(viewstate)
                                    }
                                )
                            }
                        }

                        updateEditorModel();

                        window.onresize = function () {
                            editor.layout();
                        };
                    });
                '''
                editor.insert(editorContainer)

    with open('faros-report.html', 'w') as f:
        print(editor, file=f)
