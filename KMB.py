# -*- coding: UTF-8  -*-
##
##Future improvements:
##creator templats
##keep a record of id, author
##
import cgi
import webapp2
import urllib2, urllib
from urllib2 import URLError, HTTPError
from httplib import HTTPException
from xml.dom.minidom import parse
#
class MainPage(webapp2.RequestHandler):
    def get(self):
        ID = self.request.get('ID')
        reason = self.request.get('reason')
        self.response.out.write(Format.header(u'Ange KMB ID'))
        if not len(reason) == 0:
            self.response.out.write(reason)
        else:
            self.response.out.write(u'''Ange ett 14-siffrigt ID. <br/>''')
        self.response.out.write(u'''
              <form action="result" method="post">
                <div><input value="%s" name="ID"></div>
                <div><input type="submit" value="Ange KMB ID"></div>
              </form>''' % ID)
        self.response.out.write(u'''
              <i>För att hitta id-numret är den enklaste metoden att navigera till bildens sida hos KMB.<br/>
                 Url:en innehåller texten "id=" följt av det 14-siffriga nummer som behövs.<br/>
              </i>''')
        self.response.out.write(Format.footer())
#
class KMB(webapp2.RequestHandler):
    def post(self):
        ID = self.request.get('ID').strip()
        self.redirect('/kmb/result?' + urllib.urlencode({'ID': ID}), abort=True)
    def get(self):
        run = True
        ID = self.request.get('ID').strip()
        #ID = '16001000034444'             #no license, copyright="RAÄ"
        #ID = '16000200093942'             #no license, ns5:copyright="Riksantikvarieämbetet", pres:copyright="Kontakta ATA"
        #ID = '16000200060583'             #PD-license, copyright="Utgången upphovsrätt"
        #ID = '16001000212444'             #CC-BY, copyright="RAÄ"
        #ID = '16001000149876'             #Danmark
        if (not len(ID) == 14) or (not ID.isdigit()): #invalid
            self.redirect('/kmb/?' + Format.urlencode({'ID': ID, 'reason': u'Sorry men %s är inte ett 14-siffrigt nummer. Försök igen.' % ID}), abort=True)
        try:
            fil = urllib2.urlopen('http://kulturarvsdata.se/raa/kmb/'+ID)
        except HTTPError as e:
            run = False
            self.response.out.write(Format.header(u'Problem med KMB id: %s' %ID))
            self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyvärr inte leverera datan. Säker på att du angivit rätt id?<br/>')
            self.response.out.write(u'Felkod: %d' % e.code)
            self.response.out.write(Format.footer())
        except HTTPException as e:
            run = False
            self.response.out.write(Format.header(u'Problem med KMB id: %s' %ID))
            self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyvärr inte leverera datan. <br/>')
            self.response.out.write(cgi.escape(str(e)))
            self.response.out.write(Format.footer())
        except URLError as e:
            run = False
            self.response.out.write(Format.header(u'Problem med KMB id: %s' %ID))
            self.response.out.write(cgi.escape(e.reason[0]))
            self.response.out.write(Format.footer())
        else:
            self.response.out.write(Format.header(u'Resultat för KMB-nr: %s' % ID))
            self.response.out.write(u'Objektid: <a href="http://kulturarvsdata.se/raa/kmb/html/%s" target="_blank">%s</a><br/>' % (cgi.escape(ID),cgi.escape(ID)))
            A = {'ID' : ID}
            #convert to xml:
            dom = parse(fil)
            #close file because we dont need it anymore:
            fil.close()
            del fil
            KMB.parser(dom, A)
            if not A['problem'] == None:
                run = False
                self.response.out.write(A['problem'])
                self.response.out.write(Format.footer())
        if run:
            #produce template
            template = KMB.createTemplate(A)
            self.response.out.write('<img src="%s" alt="preview"/><br/>' % A['thumbnail'])
            destFile = u'%s - kmb.%s.jpg' % (A['namn'], A['ID'])
            magnusurl = u'//tools.wmflabs.org/url2commons/index.html?urls=%s %s|%s&desc=$DESCRIPTOR$&run=1' % (A['source'], destFile, urllib.quote(template.replace('\n','$NL$').encode("utf-8")))
            self.response.out.write(u'<a href="%s" target="_blank"><button>Upload the image directly as "%s"</button></a><br />' % (magnusurl ,destFile))
            #self.response.out.write('Download the (non-thumbnail) image from <a href="'+A['source']+'" target="_blank">here</a><br/>')
            #produce template
            self.response.out.write(u'The following is automagically copied into the image description:<br/><pre>')
            self.response.out.write(cgi.escape(template))
            self.response.out.write('</pre>')
            self.response.out.write(Format.footer())
        #done
    #
    @staticmethod
    def parser(dom, A):
        A['problem'] = None
        #tags to get
        tagDict = {'namn': ('ns5:itemLabel', None),           #namn
                   'beskrivning': ('pres:description', None), #med ord
                   'byline' : ('pres:byline', None),          #Okänd, Okänd -> {{unknown}}. kasta om sa "efternamn, fornamn" -> "fornamn efternamn".
                   'motiv': ('pres:motive', None),            #också namn? use only if different from itemLabel
                   'copyright' : ('pres:copyright', None),    #RAÄ or Utgången upphovsrätt note that ns5:copyright can be different
                   'license' : ('ns5:mediaLicense', None),    #good as comparison to the above
                   'source' : ('ns5:lowresSource', None),     #source for image (hook up to download) can I check for highres?
                   'dateFrom' : ('ns5:fromTime', None),
                   'dateTo' : ('ns5:toTime', None),           #datum kan saknas
                   'bildbeteckning': ('pres:idLabel', None),  #bildbeteckning
                   'landskap': ('ns5:provinceName', None),
                   'lan' : ('ns5:countyName', None),
                   'land' : ('ns5:country', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/country#'),
                   'kommun' : ('ns6:municipality', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/municipality#'),
                   'kommunName' : ('ns5:municipalityName', None),
                   'socken' : ('ns6:parish', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/parish#'),
                   'sockenName' : ('ns5:parishName', None),
                   'thumbnail' : ('ns5:thumbnailSource', None)}
        #also has muni, kommun etc. combine some of these (linked to sv.wiki?) into "place"
        #if cc-by then include byline in copyright/license
        for tag in tagDict.keys():
            xmlTag = dom.getElementsByTagName(tagDict[tag][0])
            if not len(xmlTag) ==0:
                if tagDict[tag][1] == None:
                    A[tag] = xmlTag[0].childNodes[0].data.strip('"')
                else:
                    A[tag] = xmlTag[0].attributes[tagDict[tag][1]].value[len(tagDict[tag][2]):]
            else:
                A[tag] = ''
        #do coordinates separately
        xmlTag = dom.getElementsByTagName('georss:where')
        if not len(xmlTag) == 0:
            xmlTag = xmlTag[0].childNodes[0].childNodes[0]
            cs = xmlTag.attributes['cs'].value
            #dec = xmlTag.attributes['decimal'].value
            coords = xmlTag.childNodes[0].data.split(cs)
            if len(coords) == 2:
                A['latitude'] =coords[1][:8]
                A['longitude'] =coords[0][:8]
            else:
                A['problem'] = u'Complain to Lokal_Profil: coord was not a point : %s' % A['ID']
        #do visualizes separately need not be shm/fmi/bbr etc. can be multiple
        A['bbr']=A['fmis']=False
        xmlTag = dom.getElementsByTagName('ns5:visualizes')
        if not len(xmlTag) == 0:
            A['avbildar'] = []
            for x in xmlTag:
                url = x.attributes['rdf:resource'].value
                if url.startswith('http://kulturarvsdata.se/raa/fmi/'):
                    A['fmis']=True
                    crop = len('http://kulturarvsdata.se/raa/fmi/')
                    A['avbildar'].append('{{Fornminne|'+url[crop:]+'}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbr/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbr/')
                    num = url[crop:crop+3]
                    typ=''
                    if num == '214':
                        typ = '|b'
                    elif num == '213':
                        typ = '|a'
                    elif num == '212':
                        typ = '|m'
                    A['avbildar'].append('{{BBR|'+url[crop:]+typ+'}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbra/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbra/')
                    A['avbildar'].append('{{BBR|'+url[crop:]+'|a}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbrb/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbrb/')
                    A['avbildar'].append('{{BBR|'+url[crop:]+'|b}}')
                elif url.startswith('http://kulturarvsdata.se/raa/bbrm/'):
                    A['bbr']=True
                    crop = len('http://kulturarvsdata.se/raa/bbrm/')
                    A['avbildar'].append('{{BBR|'+url[crop:]+'|m}}')
                else:
                    A['avbildar'].append(url)
        #and an attempt at determining caegories
        xmlTag = dom.getElementsByTagName('ns5:itemClassName')
        if not len(xmlTag) == 0:
            A['tagg'] = []
            for x in xmlTag:
                A['tagg'].append(x.childNodes[0].data.strip())
        else:
            A['tagg'] = []
        xmlTag = dom.getElementsByTagName('ns5:itemKeyWord')
        if not len(xmlTag) == 0:
            if len(A['tagg'])==0:
                A['tagg'] = []
            for x in xmlTag:
                A['tagg'].append(x.childNodes[0].data.strip())
        #memory seems to be an issue so kill dom
        del dom, xmlTag
        #create date field (can one exist and the other not?)
        if A['dateFrom'] == A['dateTo']:
            A['date'] = A['dateFrom']
        elif (A['dateFrom'][:4] == A['dateTo'][:4]) and (A['dateFrom'][5:] == '01-01') and (A['dateTo'][5:] == '12-31'):
            A['date'] = A['dateFrom'][:4]
        else:
            A['date']='{{other date|between|'+A['dateFrom']+'|'+A['dateTo']+'}}'
        #rejigg byline
        if (A['byline'] == u'Okänd, Okänd') or (A['byline'] == u'Okänd'):
            A['byline'] = '{{unknown}}'
        elif len(A['byline'])==0:
            A['byline'] = '{{not provided}}'
        else:
            bySplit = A['byline'].split(',')
            if len(bySplit)==2:
                A['byline'] = (bySplit[1]+' '+bySplit[0]).strip()
            elif len(bySplit)==1:
                A['byline'] = bySplit[0]
            else:
                pass
        ##Creator
        #spot correct copyright (don't include name if unknown)
        if len(A['license'])>0:
            trim = 'http://kulturarvsdata.se/resurser/License#'
            A['license'] = A['license'].strip()[len(trim):]
        #if not copyright = RAÄ and if license='' then, this is probably unfree
        if (A['license'] == u'pdmark') or (A['copyright'].strip() == u'Utgången upphovsrätt'):
            A['license'] = u'{{PD-Sweden-photo}}'
        elif (A['license'] == u'by') or (A['copyright'].strip() == u'RAÄ'):
            #consider changing this to AND since there ight be a cc-by image which isn't from RAA.
            #Alternatively have another if inside which checks whethere copyright = RAA
            param=u'}}'
            if (A['byline'] == '{{unknown}}') or (A['byline'] == '{{not provided}}'):
                pass
            else:
                param = u'|%s}}' % A['byline']
            A['license'] = u'{{CC-BY-RAÄ‎%s' %param
        else:
            A['problem'] = u'''
                          Det verkar tyvärr som om licensen inte är fri. Copyright="%s", License="%s".<br/>
                          <small>Om informationen ovan är inkorrekt så informera gärna Lokal_Profil.</small>''' % (A['copyright'],A['license'])
        return A
    #
    @staticmethod
    def createTemplate(A):
        txt =  u'{{Kulturmiljöbild-image\n'
        txt += u'|short title = %s\n' % A['namn']
        txt += u'|original description = %s\n' % A['beskrivning']
        txt += u'|wiki description = '
        if not A['motiv'] == A['namn']:
            txt += u'%s ' % A['motiv']
        if 'avbildar' in A.keys():
            for av in A['avbildar']:
                txt += u'%s ' % av
        txt += u'\n'
        #txt += u'|photographer = '+A['byline']+'\n'
        txt += u'|photographer = {{safesubst:User:Lokal_Profil/nycklar/creators|%s|t}}\n' % A['byline']
        if len(A['land'])==0 or A['land']=='se':
            #kommunTemp
            kommunLink = A['kommunName']
            if not any(A['kommunName'].endswith(x) for x in ('a','o','u',u'å','e','i','y',u'ä',u'ö','s','x')):   #add s if kommun does not end in s or a vowel
                kommunLink += 's'
            kommunLink += ' kommun'
            #end kommunTemp
            txt += u'|depicted place = {{Country|1=SE}}, %s, [[:sv:%s|%s]]' % (A['lan'], kommunLink, A['kommunName'])
            if len(A['socken'])>0:
                txt += u', [[:sv:{{safesubst:User:Lokal_Profil/nycklar/socknar|%s}}|%s (%s)]]\n' % (A['socken'], A['sockenName'], A['landskap'])
            else:
                txt += u'\n'
            #txt += u'|depicted place = Sweden, %s, [[:sv:{{safesubst:User:Lokal_Profil/nycklar/kommuner|%s}}|%s]], [[:sv:{{safesubst:User:Lokal_Profil/nycklar/socknar|%s}}|%s (%s)]]\n' % (A['lan'], A['kommun'], A['kommunName'], A['socken'], A['sockenName'], A['landskap'])
        else:
            txt += u'|depicted place = {{Country|1=%s}}\n' % A['land'].upper()
        txt += u'|date = %s\n' % A['date']
        txt += u'|permission = %s\n' % A['license']
        txt += u'|ID = %s\n' % A['ID']
        txt += u'|bildbeteckning = %s\n' % A['bildbeteckning']
        txt += u'|notes = \n'
        txt += u'}}\n'
        if ('latitude' in A.keys()) and (len(A['latitude'])>0):
            txt += u'{{Object location dec|%s|%s}}\n' % (A['latitude'],A['longitude'])
        txt += u' \n'
        txt += u'[[Category:Uploaded with KMB tool]]\n'
        txt += u'{{safesubst:User:Lokal_Profil/nycklar/creators|%s|c}}\n' % A['byline']
        if A['fmis']:
            txt += u'[[Category:Archaeological monuments in %s]]\n' % A['landskap']
            txt += u'[[Category:Archaeological monuments in %s County]]\n' % A['lan']
        if A['bbr']:
            txt += u'[[Category:Protected buildings in Sweden]]\n'
        #must be better to do this via safesubst
        if len(A['tagg']) > 0:
            for tagg in A['tagg']:
                txt += u'{{safesubst:User:Lokal_Profil/nycklar/cats|%s|%s|%s}}\n' % (tagg, A['land'].upper(), A['landskap'])
        return txt
    #
#
class Format:
    @staticmethod
    def urlencode(aDict):
        '''This ensures that every object of a dict is utf-8 encoded'''
        eDict = {}
        for k, v in aDict.iteritems():
            if isinstance(v, list):              #for lists each object must be encoded
                tmp=''
                for i in v:
                    tmp+='|'+unicode(i).encode('utf-8')
                eDict[k] = tmp
            else:
                eDict[k] = unicode(v).encode('utf-8')
        return urllib.urlencode(eDict)
    @staticmethod
    def header(title):
        txt ='''
          <html>
            <head>
              <title>%s</title>
            </head>
            <body>''' % title
        return txt
    @staticmethod
    def footer():
        txt = '''
              <hr>
                <small>If you have any problems or questions please contact <a href="https://sv.wikipedia.org/wiki/Anv%C3%A4ndardiskussion:Lokal_Profil" target="_blank">Lokal_Profil</a>.</small><br/>
                <small>Source code <a href="https://github.com/lokal-profil/RAA-tools">at Github</a>.</small>
            </body>
          </html>'''
        return txt
    #
#

app = webapp2.WSGIApplication([('/kmb/', MainPage),
                               ('/kmb/result', KMB)],
                              debug=True)
