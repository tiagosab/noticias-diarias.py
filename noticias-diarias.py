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
import BeautifulSoup
from Tkinter import *

import gdata.blogger.client
import gdata.client
import gdata.blogger.service

url_nacionais = "http://www.itamaraty.gov.br/sala-de-imprensa/selecao-diaria-de-noticias/midias-nacionais"

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
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                self.links[tag]()
                return


class App:
    def __init__(self, master, noticias):
        self.master = master

        self.mainframe = Frame(master)
        self.textframe = Frame(self.mainframe)
        self.buttonframe = Frame(self.mainframe)
        self.textframe.pack(side=BOTTOM, fill="both", expand=True)
        self.buttonframe.pack(side=TOP)
        self.mainframe.pack(fill="both", expand=True)

        self.noticias = noticias
        self.indice = noticias.index
        self.current = ''
        self.text = ()

        self._makebuttons()
        self.insert_index()

    def _makebuttons(self):
        self.button = Button(self.buttonframe,
                             text="QUIT",
                             fg="red",
                             command=self.mainframe.quit)
        self.button.pack(side=LEFT)

        self.indexbutton = Button(self.buttonframe,
                                  text="Índice",
                                  command=self.insert_index)
        self.indexbutton.pack(side=LEFT)

        self.blogbutton = Button(self.buttonframe,
                                 text="Blog",
                                 command=self.blognow)
        self.blogbutton.pack()

        self.errorbutton = Button(self.buttonframe,
                                  text="Deu erro?",
                                  command=self.handle_error)
        self.errorbutton.pack(side=RIGHT)

    def get_string(self, txt, **kwargs):
        """kwargs are passed to Entry. Use width and show."""
        win = Toplevel()
        Label(win, text=txt).pack()
        st = StringVar()
        Entry(win, textvariable=st, **kwargs).pack()
        Button(win, text="Tá bom", command=win.destroy).pack()
        self.master.wait_window(win)
        return st.get()

    def blognow(self):
        username = self.get_string("Email", width=60)
        passwd = self.get_string("Senha", width=20)

        blog = Blog(username, passwd, '')
        st = blog.getblogs()
        new = Toplevel()
        textframe = Frame(new)
        text = Text(textframe)
        textframe.pack()
        text.pack()
        text.insert(INSERT, st)

    def handle_error(self):
        import tkFileDialog, tkMessageBox, os
        if tkMessageBox.askokcancel(title="Gravação de registro de erro.",
            message="""Você deseja gravar o registro de erro em um arquivo?
Caso o deseje, aperte em ok e escolha o nome e a localização do arquivo.
Envie-o a seguir para tiagosaboga@gmail.com"""):
            f = tkFileDialog.asksaveasfile(defaultextension='txt', initialfile="erro-noticias-diarias.txt")
            f.write("OUTPUT\n")
            f.write(self.text.get('1.0', END))
            f.write("\n---------------\n")
            if self.current:
                f.write(self.noticias.get_emergency_string(self.current))
            f.close()
     
    def insert_index(self):
        if not self.text:
            scrollbar = Scrollbar(self.textframe)
            scrollbar.pack(side=RIGHT, fill=Y)
            self.text = Text(self.textframe,
                             bg='white',
                             yscrollcommand=scrollbar.set,
                             state=DISABLED)
            scrollbar.config(command=self.text.yview)
        else:
            self.remove_index()
        if self.current:
            self.current = ''
        self.text['state']=NORMAL
        self.hyperlink = HyperlinkManager(self.text)
        for name_jornal, (link_jornal, titulos) in self.indice.items():
            self.text.insert(INSERT, "%s\n" % name_jornal)
            for manchete, link_materia in titulos:
                self.text.insert(INSERT,
                  "%s\n" % manchete,
                     self.hyperlink.add(
                       self.get_callback(
                         manchete,
                         name_jornal,
                         link_jornal,
                         link_materia)))
        self.text['state']=DISABLED
        self.text.pack(fill="both", expand=True)
    def insert_text(self, manchete, name_jornal, link):
        self.current = link
        self.remove_index()
        self.text['state']=NORMAL
        self.text.insert(INSERT,
                         "%s" % self.noticias.get_noticia(link))
        self.text['state']=DISABLED
    def remove_index(self):
        self.text['state']=NORMAL
        self.text.delete('1.0', END)
        self.text['state']=DISABLED
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
    def get_emergency_string(self, link):
        return "RAW\n%s\n-------------\nPRETTY\n%s" % (self.noticias[link].rawtag.prettify(),
                                                       self.noticias[link].rawtxt)
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
        return noticia.gettext()

class Noticia(object):
    def __init__(self, link):
        self.link = link
        self.rawtxt = get_url(link)
        self.rawtag = self.extract_noticia(self.rawtxt)
        try:
            self.title = self.rawtag.h1
            self.date = self.rawtag.find('p', text=re.compile('^\d{2}/\d{2}/\d{4}$'))
            self.name = self.date.findNext('p')
            self.section = self.name.findNext('span')
            self.subtitle = self.rawtag.find('div', {'id': 'subTituloAreaMateria'})
##            self.text = (self.rawtag.find('div', {'id': 'textoAreaMateria'})
##                    or
##                    self.rawtag.find('div', {'class': "documentDescription"}))
##            title, date, name, section, subtitle = self.tostring(title, date, name, section, subtitle)
            self.text = self.extract_text_noticia(self.rawtag)   #(text)
            if not self.text:
                print noticia.prettify()
                raise Exception
        except AttributeError:
            print noticia.prettify()
            raise
    def gettext(self):
        #print self.rawtag
        #print "$$$%s$$$" % self.text
        ret = ''
        for data in [self.title,
                     self.date,
                     self.name,
                     self.section,
                     self.subtitle,
                     self.text]:
            try:
                ret += "\n%s" % data
            except:
                continue
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
        return '\n'.join(txt)   
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

class Blog(object):
    def __init__(self, username, passwd, captchahandler):
        """Creates a GDataService and provides ClientLogin auth details to it.
        The email and password are required arguments for ClientLogin.  The
        'source' defined below is an arbitrary string, but should be used to
        reference your name or the name of your organization, the app name and
        version, with '-' between each of the three values."""
        self._auth(username, passwd)

    def _auth(self, username, passwd):
        self.client = gdata.blogger.service.BloggerService(email=username,
                                                           password=passwd,
                                                           account_type='GOOGLE',
                                                           source='noticias-diarias-0.1')
        # try:
        #     service.ProgrammaticLogin()
        # except:
        #     raise

        # self.client = gdata.blogger.client.BloggerClient()
        # self.client.source = 'noticias-diarias-0.1'
        # self.client.service = 'blogger'
        # self.client.account_type = 'GOOGLE'
        # self.client.server = 'www.blogger.com'
        # self.client.ProgrammaticLogin()

    def getblogs(self):
        feed = self.client.get_blogs()
        ret = feed.title.text
        for entry in feed.entry:
            ret = "%s\n%s" % (ret, entry.title.text)
        return ret

def get_url(url):
    headers = {'Accept': 'text/html'}
    rqs = urllib2.Request(url=url, headers=headers)
    return urllib2.urlopen(rqs).read()

def save_file(filename, txt):
    import os.path
    f=open(filename, 'w')
    f.write(txt)
    f.close()

def main():
    noticias = Noticias(url_nacionais)
    root = Tk()
    app = App(root, noticias)
    app.master.title("Noticias diárias")
    root.mainloop()

if __name__=="__main__":
    main()
