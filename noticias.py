#!/usr/bin/python
# -*- coding=utf-8 -*-

# Copyright (C) 2010 Tiago Saboga <tiagosaboga@gmail.com>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# 2010-05-27 - Align buttons
#            - Add scrollbar
#            - Make text frame resizable

import urllib2
import re
import os
import BeautifulSoup
import Tkinter as tk
import tkMessageBox
import ConfigParser

import gdata.blogger.client
import gdata.client
import gdata.blogger.service
import gdata.service as gserv
import atom

url_nacionais = "http://www.itamaraty.gov.br/sala-de-imprensa/selecao-diaria-de-noticias/midias-nacionais"
conffile = 'notidi.conf'
blogname = 'crascóriafanos'

class Config(ConfigParser.SafeConfigParser):
    def __init__(self):
        # self.config = SafeConfigParser()
        ConfigParser.SafeConfigParser.__init__(self)
        sections = {'blog': ['username', 'password']}
        for section in sections:
            self.add_section(section)
            for option in sections[section]:
                self.set(section, option, '')
        try:
            from win32com.shell import shellcon, shell            
            basedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
            homedir = os.path.join(basedir, 'notidi')
        except ImportError: # quick semi-nasty fallback for non-windows/win32com case
            homedir = os.path.join(os.path.expanduser("~"), '.notidi')
        if not os.path.exists(homedir):
            os.mkdir(homedir)
        if not os.path.isdir(homedir):
            raise Exception
        filename = conffile
        if os.path.exists(filename):
            try:
                self.read(filename)
            except:
                raise


class HyperlinkManager:
    """Taken  from http://effbot.org/zone/tkinter-text-hyperlink.htm"""
    def __init__(self, text):

        self.text = text

        self.text.tag_config("hyper", foreground="blue", underline=1)

        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Button-1>", self._click)

        self.reset()

    def reset(self):
        self.links = {}

    def add(self, action):
        # add an action to the manager.  returns tags to use in
        # associated text widget
        tag = "hyper-%d" % len(self.links)
        self.links[tag] = action
        return "hyper", tag

    def _enter(self, event):
        self.text.config(cursor="hand2")

    def _leave(self, event):
        self.text.config(cursor="")

    def _click(self, event):
        for tag in self.text.tag_names(tk.CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag]()
                return

class App:
    def __init__(self, master, noticias):
        self.master = master
        self.config = Config()

        self.mainframe = tk.Frame(master)
        self.textframe = tk.Frame(self.mainframe)
        self.buttonframe = tk.Frame(self.mainframe)
        self.textframe.pack(side=tk.BOTTOM, fill="both", expand=True)
        self.buttonframe.pack(side=tk.TOP)
        self.mainframe.pack(fill="both", expand=True)

        self.noticias = noticias
        self.indice = noticias.index
        self.blog = None
        self.current = ''
        self.text = ()

        self._makebuttons()
        self.insert_index()

    def _makebuttons(self):
        self.button = tk.Button(self.buttonframe,
                                text="Sair",
                                fg="red",
                                command=self.mainframe.quit)
        self.button.pack(side=tk.LEFT)

        self.indexbutton = tk.Button(self.buttonframe,
                                     text="Índice",
                                     command=self.insert_index)
        self.indexbutton.pack(side=tk.LEFT)

        self.blogbutton = tk.Button(self.buttonframe,
                                    text="Blog",
                                    command=self.blognow)
        self.blogbutton.pack()

        self.errorbutton = tk.Button(self.buttonframe,
                                     text="Deu erro?",
                                     command=self.handle_error)
        self.errorbutton.pack(side=tk.RIGHT)

    def get_string(self, txt, **kwargs):
        """kwargs are passed to Entry. Use width and show."""
        win = tk.Toplevel()
        tk.Label(win, text=txt).pack()
        st = tk.StringVar()
        tk.Entry(win, textvariable=st, **kwargs).pack()
        tk.Button(win, text="Tá bom", command=win.destroy).pack()
        self.master.wait_window(win)
        return st.get()
    def getuserpass(self):
        username = self.config.get('blog', 'username')
        password = self.config.get('blog', 'password')
        if not username:
            username = self.get_string("Email", width=70)
            self.config.set('blog', 'username', username)
        if not password:
            password = self.get_string("Senha", width=20, show='*')
            self.config.set('blog', 'password', username)
        return username, password

    def blognow(self):
        if not self.blog:
            username, password = self.getuserpass()
            captcha_response = None
            while not self.blog:
                try:
                    self.blog = Blog(username,
                                     password,
                                     captcha_response=captcha_response)
                except gserv.CaptchaRequired:
                    captcha_response = self.show_captcha(self.blog.captcha_url)
                    self.blog = None
                except gserv.BadAuthentication:
                    self.show_error("Erro de autenticação.")
                    return
                except:
                    self.show_error("Erro não previsto.")
                    raise
            try:
                self.blog.connect()
            except BlogNotFound:
                self.showblogs()
        if self.current:
            self.blog.post(self.current.title,
                           self.current.text,
                           self.current.date)
    def showblogs(self):
        st = self.blog.getblogs()
        new = tk.Toplevel()
        textframe = tk.Frame(new)
        text = tk.Text(textframe)
        textframe.pack()
        text.pack()
        text.insert(tk.INSERT, st)
    def show_error(self, txt):
        message = tkMessageBox.showerror(title="Notícias diárias - ERRO",
                                         message=txt)
    def show_captcha(self, captcha_url):
        new = tk.Toplevel()
        textframe = tk.Frame(new)
        text = tk.Text(textframe)
        textframe.pack()
        text.pack()
    def handle_error(self):
        import tkFileDialog, tkMessageBox, os
        if tkMessageBox.askokcancel(title="Gravação de registro de erro.",
            message="""Você deseja gravar o registro de erro em um arquivo?
Caso o deseje, aperte em ok e escolha o nome e a localização do arquivo.
Envie-o a seguir para tiagosaboga@gmail.com"""):
            f = tkFileDialog.asksaveasfile(defaultextension='txt', initialfile="erro-noticias-diarias.txt")
            f.write("OUTPUT\n")
            f.write(self.text.get('1.0', tk.END).encode('utf-8'))
            f.write("\n---------------\n")
            if self.current:
                str_ = u"RAW\n%s\n-------------\nPRETTY\n%s"
                emergency = str_ % (self.current.rawtag.prettify(),
                                    self.current.rawtxt.decode('utf-8',
                                                               'ignore'))
                f.write(emergency.encode('utf-8'))
            f.close()
    def insert_index(self):
        if not self.text:
            scrollbar = tk.Scrollbar(self.textframe)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.text = tk.Text(self.textframe,
                             bg='white',
                             yscrollcommand=scrollbar.set,
                             state=tk.DISABLED)
            scrollbar.config(command=self.text.yview)
        else:
            self.remove_index()
        if self.current:
            self.current = ''
        self.text['state']=tk.NORMAL
        self.hyperlink = HyperlinkManager(self.text)
        for name_jornal, (link_jornal, titulos) in self.indice.items():
            self.text.insert(tk.INSERT, "%s\n" % name_jornal)
            for manchete, link_materia in titulos:
                self.text.insert(tk.INSERT,
                  "%s\n" % manchete,
                     self.hyperlink.add(
                       self.get_callback(
                         manchete,
                         name_jornal,
                         link_jornal,
                         link_materia)))
        self.text['state']=tk.DISABLED
        self.text.pack(fill="both", expand=True)
    def insert_text(self, manchete, name_jornal, link):
        self.current = self.noticias.get_noticia(link)
        self.remove_index()
        self.text['state'] = tk.NORMAL
        self.text.insert(tk.INSERT,
                         "%s" % self.current)
        self.text['state']=tk.DISABLED
    def remove_index(self):
        self.text['state']=tk.NORMAL
        self.text.delete('1.0', tk.END)
        self.text['state']=tk.DISABLED
    def get_callback(self, manchete, name_jornal, link_jornal, link_materia):
        def open_materia():
            self.insert_text(manchete, name_jornal, "%s/%s" % (link_jornal, link_materia))
        return open_materia

class Noticias(object):
    """
A classe Noticias é responsável por baixar e manter organizadas as
notícias individuais e os índices.

Uma função retorna o índice, com todos os títulos das matérias
organizados por jornal. Num segundo momento, deverão vir acompanhados
também de um indicador de estado da notícia (marcada como importante,
não lida, lida).

Caso seja necessário, outra função retornará o texto da matéria, a
partir do título da matéria e do nome do jornal. Aqui também deverá
vir o indicador de estado da notícia."""
    def __init__(self, link_indice):
        txt = get_url(link_indice)
        self.index = self.index_build(txt)
        self.noticias = {}
    def get_titulos(self, jornal):
        """jornal is a BeautifulTag"""
        titulos = []
        manchetes = jornal.findAll('ul')
        for m in manchetes:
            name = m.a.string
            link = m.a['href']
            titulos.append((name, link))
        return titulos
    def index_build(self, txt):
        index = {}
        soup = BeautifulSoup.BeautifulSoup(txt)
        tabl = soup.first('ul', {'yal:omit-tag': ''})
        jornais = tabl.findAll(name="ul", recursive=False)
        for j in jornais:
            name = j.a.strong.string
            link = j.a['href']
            titulos = self.get_titulos(j)
            index[name]=(link, titulos)
        return index
    def get_noticia(self, link):
        noticia = self.noticias.get(link, None)
        if not noticia:
            noticia = Noticia(link)
            self.noticias[link] = noticia
        return noticia

class Noticia(object):
    def __init__(self, link, rawtxt=None):
        self.link = link
        self.rawtxt = rawtxt or get_url(link)
        self.rawtag = self.extract_noticia(self.rawtxt)
        try:
            self._extractdata()
        except AttributeError:
            print self.rawtag.prettify()
            raise
    def _find(self, tagstr, attrs):
        tag = self.rawtag.find(tagstr, attrs)
        return ''.join(self._descend_into_tags(tag))
    def _extractdata(self):
        self.title = self._find('h1', {'id': "parent-fieldname-title"})
        self.date = self._find('div', {'id': 'parent-fieldname-Data'})
        self.section = self._find('span', {'id': 'parent-fieldname-Assunto'})
        self.subtitle = self._find('div', {'id': 'subTituloAreaMateria'})
        self.author = self._find('span', {'class': 'parent-fieldname-Credito'})
        self.text = self.extract_text_noticia(self.rawtag)
        if not self.text:
            print self.rawtag.prettify()
            raise Exception
    def __str__(self):
        return self.gettext()
    def gettext(self):
        ret = u''
        for data in [self.title,
                     self.date,
                     self.section,
                     self.subtitle,
                     self.text]:
            ret += u"\n%s" % unicode(data)
        return ret
    def extract_noticia(self, txt):
        soup = BeautifulSoup.BeautifulSoup(txt)
        try:
            noticia = soup.find('div', {'id': 'content'})
        except:
            return txt
        return noticia
    def _descend_into_tags(self, tag):
        txt = []
        if not tag:
            return ['']
        for item in tag:
            if type(item) is BeautifulSoup.NavigableString:
                txt.append(item.replace('\r\n', '\n'))
            elif type(item) is BeautifulSoup.Tag:
                if len(item)>0:
                    self._descend_into_tags(item)
                else:
                    if item.name=='br':
                        if txt and txt[-1]!='\n':
                            txt.append('\n')
                    else:
                        txt.append(item.name)
        return txt
    def extract_text_noticia(self, tag):
        txt = []
        for p in tag.findAll('p'):
            txt.extend(self._descend_into_tags(p))
        return '\n'.join(txt).replace('\n\n\n', '\n\n')
    def tostring(self, *args):
        ret = []
        for arg in args:
            # print type(arg)
            try:
                st = arg.string
            except AttributeError:
                st = unicode(arg)
            if not st:
                st = ''
                for a in arg:
                    try:
                        st += self.tostring(a)
                    except:
                        # print "st: %s\ntype: %s" % (st, type(st))
                        pass
            ret.append(st)
        return ret

class BlogNotFound(Exception):
    pass

class Blog(object):
    def __init__(self, username, passwd, captcha_response=None):
        """Creates a GDataService and provides ClientLogin auth details to it.
        The email and password are required arguments for ClientLogin.  The
        'source' defined below is an arbitrary string, but should be used to
        reference your name or the name of your organization, the app name and
        version, with '-' between each of the three values."""
        self._auth(username, passwd, captcha_response=captcha_response)

    def connect(self):
        self.catulombo = self.getcatulombo()
        if not self.catulombo:
            raise BlogNotFound

    def _auth(self, username, passwd, captcha_response=None):
        self.client = gdata.blogger.service.BloggerService(email=username,
                                                           password=passwd,
                                                           account_type='GOOGLE',
                                                           source='noticias-diarias-0.1')
        if captcha_response:
            captcha_token = self.client.captcha_token
        else:
            captcha_token = None
        try:
            self.client.ProgrammaticLogin(captcha_response=captcha_response,
                                          captcha_token=captcha_token)
        except gserv.CaptchaRequired:
            self.captchahandler(self.client.captcha_url)
        except gserv.BadAuthentication:
            raise
    def getblogs(self):
        feed = self.client.GetBlogFeed()
        ret = feed.title.text
        for entry in feed.entry:
            ret = "%s\n%s" % (ret, entry.title.text)
        return ret
    def getcatulombo(self):
        feed = self.client.GetBlogFeed()
        for entry in feed.entry:
            if entry.title.text.upper()==blogname.upper():
                return entry
    def post(self, title, text, date):
        blogentry = gdata.blogger.BloggerEntry()
        blogentry.title = atom.Title('xhtml', title)
        blogentry.content = atom.Content(content_type='html', text=text)
        # format of date is date-time, as in
        # http://tools.ietf.org/html/rfc3339 (date in internet)
        # http://tools.ietf.org/html/rfc4287#section-3.3 (atom format)
        blogentry.published = atom.Published(text='2010-12-31T14:03:57-03:00')
        self.client.AddPost(blogentry, blog_id=self.catulombo.GetBlogId())

def get_url(url):
    headers = {'Accept': 'text/html'}
    rqs = urllib2.Request(url=url, headers=headers)
    return urllib2.urlopen(rqs).read()

def setup_proxy():
    os.environ['http_proxy'] = 'http://proxy.mre.gov.br:3128' 
    os.environ['https_proxy'] = 'https://proxy.mre.gov.br:3128' 
    # os.environ['proxy-username'] = 'user' 
    # os.environ['proxy-password'] = 'pass' 

def save_file(filename, txt):
    import os.path
    f=open(filename, 'w')
    f.write(txt)
    f.close()

class Erro(object):
    def __init__(self, txt):
        result = re.match('OUTPUT(.*)', txt)

def import_erro(filename):
    return Erro(filename.open.read())

def main():
    # setup_proxy()
    noticias = Noticias(url_nacionais)
    root = tk.Tk()
    app = App(root, noticias)
    app.master.title("Noticias diárias")
    root.mainloop()

if __name__=="__main__":
    main()
