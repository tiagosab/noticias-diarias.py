#!/usr/bin/python
# -*- coding=utf8 -*-

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

import urllib2
import re
from BeautifulSoup import BeautifulSoup
from Tkinter import *

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

        self.frame = Frame(master)
        self.frame.pack()
        self.noticias = noticias
        self.indice = noticias.index

        self.button = Button(self.frame,
                             text="QUIT",
                             fg="red",
                             command=self.frame.quit)
        self.button.pack(side=LEFT)

        self.indexbutton = Button(self.frame,
                                  text="Índice",
                                  command=self.insert_index)
        self.indexbutton.pack(side=LEFT)
        self.text = ()

        self.insert_index()
        

    def insert_index(self):
        if not self.text:
            self.text = Text(self.frame, bg='white')
        else:
            self.remove_index()
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
        self.text.pack()

    def insert_text(self, manchete, name_jornal, link):
        self.remove_index()
        self.text.insert(INSERT,
                         "%s" % self.noticias.get_noticia(link))

    def remove_index(self):
        self.text.delete('1.0', END)

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
        soup = BeautifulSoup(txt)
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
            txt = get_url(link)
            noticia = self.extract_noticia(txt)
            self.noticias[link] = noticia
        return noticia

    def extract_noticia_orig(self, txt):
        soup = BeautifulSoup(txt)
        noticia = soup.find('div', {'id': 'content'})
        return noticia

    def tostring(self, *args):
        ret = []
        for arg in args:
            try:
                st = arg.string
            except AttributeError:
                st = unicode(arg)
            ret.append(st)
        return ret

    def extract_noticia(self, txt):
        soup = BeautifulSoup(txt)
        try:
            noticia = soup.find('div', {'id': 'content'})
            print noticia.prettify()
            title = noticia.h1
            date = noticia.find('p', text=re.compile('^\d{2}/\d{2}/\d{4}$'))
            name = date.findNext('p')
            section = name.findNext('span')
            subtitle = noticia.find('div', {'id': 'subTituloAreaMateria'})
            text = noticia.find('div', {'id': 'textoAreaMateria'})
            print text.prettify()
            title, date, name, section, subtitle, text = self.tostring(title, date, name, section, subtitle, text)
            print '1---------------1'
            print text
        except:
            raise
        return '\n'.join([title, date, name, section, subtitle, text])

def get_url(url):
    headers = {'Accept': 'text/html'}
    rqs = urllib2.Request(url=url, headers=headers)
    return urllib2.urlopen(rqs).read()

def main():
    noticias = Noticias(url_nacionais)
    # txt_indice_diario = get_url(url_nacionais)
    # indice_noticias = index_build(txt_indice_diario)

    root = Tk()
    app = App(root, noticias)
    # w = Label(root, text="Baixando notícias")
    # w.pack()

    root.mainloop()


    # for jornal, indice in indice_noticias.items():
    #     print "\n\n%s: \n" % jornal
    #     for noticia in indice[1]: # noticia is a tuple (name, link)
    #         print noticia[0] # only name
    

if __name__=="__main__":
    main()
