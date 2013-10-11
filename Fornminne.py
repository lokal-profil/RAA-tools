# -*- coding: ISO-8859-1  -*-
##
##Framtida forbattringar
##fraga om sidnamn ->mojligen flytta titel till alt_namn och ha PAGENAME som titel
##skapa lank till sida/pop-up
##beklaga klipp o klistra, skyll pa https://bugzilla.wikimedia.org/show_bug.cgi?id=12853
##Rundata i datastore, med cron-jobb som kollar om wikisidan har updaterats, och i s� fall updaterar datastore (samma med signum)
##Could possibly display thumbs
##
import cgi
import webapp2
import urllib2, urllib
from urllib2 import URLError, HTTPError
from xml.dom.minidom import parse

class MainPage(webapp2.RequestHandler):
    def get(self):
        objektid=self.request.get('objektid')
        reason = self.request.get('reason')
        self.response.out.write(Format.header(u'Ange FMIS objektid'))
        if not len(reason) == 0:
            self.response.out.write(reason)
        else:
            self.response.out.write(u'''Ange ett 14-siffrigt objektid. <br/>''')
        self.response.out.write(u'''
              <form action="result" method="post">
                <div><input value="%s" name="objektid"></div>
                <div><input type="submit" value="Ange objektid"></div>
              </form>''' % objektid)
        self.response.out.write(u'''
              <i>F�r att hitta objektid �r den enklaste metoden att via Forns�k navigera till objektets sida. I beskrivningen finns posten "Visa i Google Earth".<br/>
                 H�gerklicka p� l�nken intill och kopiera denna. Den kopierade texten inneh�ller "objektid=" f�ljt av det 14-siffriga nummer som beh�vs.
                 <br/><br/>
                 Notera att det nummer som ibland anges i Forns�ks-url:en f�r objektsidan inte n�dv�ndigtvis �r r�tt nummer.
              </i>''')
        self.response.out.write(Format.footer())


class Fornminne(webapp2.RequestHandler):
    def post(self):
        run = True                                                           #toggle for stopping processing in case of no contact with kulturarvsdata.se
        getXML = False
        objektid = self.request.get('objektid').strip()
        RAA = {'objektid' : objektid}                                        #dictionary of values aquired from objektid only
        runDict = {'results' : False}                                        #dictionary for rune related objekts
        if (not len(objektid) == 14) or (not objektid.isdigit()): #invalid
            self.redirect('/fmis/?' + Format.urlencode({'objektid': objektid, 'reason': u'Sorry men %s �r inte ett 14-siffrigt nummer. F�rs�k igen.' % objektid}), abort=True)
        #read in any variables which might have been passed from a previous objektid query
        varList = ['namn','typ','raa-nr','landskap','lan','lanName','kommun','kommunName','socken','sockenName','latitude','longitude','bild','bildCommons','commonsPics']
        for v in varList:
            RAA[v] = self.request.get(v)
            if RAA[v].startswith('|'):
                RAA[v] = Format.recoverList(RAA[v])
        #if no previous query then get xml
        if len(RAA['raa-nr'])==0:      #note that raa-nr is guaranteed to always exist for any fmis query
            getXML=True
            try:
                fil = urllib2.urlopen('http://kulturarvsdata.se/raa/fmi/'+objektid)
            except HTTPError, e:
                run = False
                self.response.out.write(Format.header(u'Problem med FMIS objektid: %s' %objektid))
                self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyv�rr inte leverera datan. S�ker p� att du angivit r�tt objektid?<br/>')
                self.response.out.write(u'Felkod: %d' % e.code)
                self.response.out.write(Format.footer())
            except URLError, e:
                run = False
                self.response.out.write(Format.header(u'Problem med FMIS objektid: %s' %objektid))
                self.response.out.write(cgi.escape(e.reason[0]))
                self.response.out.write(Format.footer())
            else:
                #convert to xml:
                dom = parse(fil)
                #close file because we dont need it anymore:
                fil.close()
                del fil
                #parse xml into RAAdict
                Fornminne.fornParser(dom, RAA)
                #freeing up memory
                del dom
                if 'problem' in RAA.keys():
                    run = False
                    self.response.out.write(Format.header(u'Problem med FMIS objektid: %s' %objektid))
                    self.response.out.write(RAA['problem'])
                    self.response.out.write(Format.footer())
                else:
                    #Check if there are images on Commons
                    RAA['commonsPics'] = Fornminne.commonsPics(RAA)
                    if RAA['commonsPics']==None:
                        run = False
                        self.response.out.write(Format.header(u'Problem med FMIS objektid: %s' %objektid))
                        self.response.out.write(cgi.escape(u'*"%s" with value <%s>' % (RAA['problem'][0],RAA['problem'][1]))+'<br/>')
                        self.response.out.write(Format.footer())
        if run:
            self.response.out.write(Format.header(u'Resultat f�r FMIS objektid: %s' %objektid))
            self.response.out.write(u'Objektid: <a href="http://kulturarvsdata.se/raa/fmi/html/%s" target="_blank">%s</a> <-- L�nk till Forns�k d�r "undertyp" samt "h�jdl�ge" kan l�sas av.<br/>' %(cgi.escape(objektid),cgi.escape(objektid)))
            #deal with special case of Runristning
            if RAA['typ'] == 'Runristning':
                signum = self.request.get('signum').strip()
                if (len(signum) == 0) and getXML:
                    signum = Fornminne.getSignum(objektid, runDict)
                    if signum == None: #if problem
                        pass
                    elif signum[1] == 1:
                        Fornminne.getSRDB(runDict, signum[0])
                    signum = signum[0]
                else:
                    Fornminne.getSRDB(runDict, signum)
                if 'problem' in runDict.keys(): # if either getSignum or getSRDB messed up
                    response = cgi.escape(u'*"%s" with value <%s>' % (runDict['problem'][0],runDict['problem'][1]))+'<br/>'
                    response += Format.footer()
                    return(response)
                runDict['signum'] = signum
                #prompt for a changed/trimmed/added signum
                self.response.out.write(u'''
                              <form action="/fmis/result?%s" method="post">
		                <input value="%s" name="signum"><input type="submit" value="�ndra signum?">
		              </form><br/>''' % (Format.urlencode(RAA),runDict['signum']) )
            #Some image suggestions
            if (len(RAA['bild'])>0) or (int(RAA['commonsPics'])>0) or ('runBild' in runDict.keys() and len(runDict['runBild'])>0):
                kmbString = 'http://kulturarvsdata.se/raa/kmb/html/'
                self.response.out.write(u'N�gra bildf�rslag:<br/>')
                if int(RAA['commonsPics'])>0:
                    self.response.out.write(u'<a href="https://commons.wikimedia.org/w/index.php?title=Special:Search&search=%s&ns0=1&ns6=1&ns14=1&redirs=1" target="_blank">Commons s�kning</a> (minst %d bilder)<br/>' % (objektid, int(RAA['commonsPics'])) )
                if 'bild' in RAA.keys():
                    for bild in RAA['bild']:
                        self.response.out.write(u'*<a href="%s" target="_blank">Fr�n FMIS</a>' % bild)
                        if bild.startswith(kmbString):
                            self.response.out.write(u' <small>(<a href="/kmb/result?ID=%s" target="_blank">Ladda upp till Commons?</a>)</small>' % bild[len(kmbString):])
                        self.response.out.write(u'<br/>')
                if runDict['results'] and (len(runDict['runBild'])>0):
                    for b in runDict['runBild']:
                        if b.startswith(u'{{KMB-l�nk|'):
                            b = 'http://kulturarvsdata.se/raa/kmb/html/'+b[len(u'{{KMB-l�nk|'):].strip('}}')
                        elif b.startswith(u'{{SHM-l�nk|bild|'):
                            b = 'http://http://kulturarvsdata.se/shm/media/html/'+b[len(u'{{SHM-l�nk|bild|'):].strip('}}')
                        if not b in RAA['bild']:                          #No need to output same again
                            self.response.out.write(u'*<a href="%s" target="_blank">Fr�n SRDB</a>' % b)
                            if b.startswith(kmbString):
                                self.response.out.write(u' <small>(<a href="/kmb/result?ID=%s" target="_blank">Ladda upp till Commons?</a>)</small>' % b[len(kmbString):])
                            self.response.out.write(u'<br/>')
            #Start writing template
            self.response.out.write(u'Kopiera in f�ljande i artikeln:<br/><pre>')
            self.response.out.write(cgi.escape(Fornminne.createTemplate(RAA, runDict)))
            self.response.out.write('</pre>')
            self.response.out.write(Format.footer())
        #done
    #
    @staticmethod
    def fornParser(dom, RAA):
        #tags to get
        tagDict = {'namn': ('ns5:itemKeyWord', None),
                   'typ': ('ns5:itemClassName', None),
                   'raa-nr' : ('ns5:number', None),
                   'landskap': ('ns6:province', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/province#'),
                   'lan' : ('ns6:county', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/county#'),
                   'kommun' : ('ns6:municipality', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/municipality#'),
                   'socken' : ('ns6:parish', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/parish#'),
                   'sockenName' : ('ns5:parishName', None),
                   'kommunName' : ('ns5:municipalityName', None),
                   'lanName' : ('ns5:countyName', None)}
        #
        for tag in tagDict.keys():
            xmlTag = dom.getElementsByTagName(tagDict[tag][0])
            if not len(xmlTag) ==0:
                if tagDict[tag][1] == None:
                    RAA[tag] = xmlTag[0].childNodes[0].data.strip('"')
                else:
                    RAA[tag] = xmlTag[0].attributes[tagDict[tag][1]].value[len(tagDict[tag][2]):]
            else:
                RAA[tag] = ''               #Makes template building easier
        #do coordinates separately
        xmlTag = dom.getElementsByTagName('georss:where')
        if not len(xmlTag) == 0:
            xmlTag = xmlTag[0].childNodes[0].childNodes[0]
            cs = xmlTag.attributes['cs'].value
            #dec = xmlTag.attributes['decimal'].value
            coords = xmlTag.childNodes[0].data.split(cs)
            if len(coords) == 2:
                RAA['latitude'] =coords[1][:8]
                RAA['longitude'] =coords[0][:8]
            else:
                RAA['problem'] = u'Complain to Lokal_Profil: coord was not a point : %s' % RAA['objektid']
        #do images separately
        xmlTag = dom.getElementsByTagName('ns5:isVisualizedBy')
        if not len(xmlTag) == 0:
            RAA['bild'] = []
            for x in xmlTag:
                url = x.attributes['rdf:resource'].value
                if url.startswith('http://kulturarvsdata.se'):
                    RAA['bild'].append(url[:url.rfind('/')]+'/html'+url[url.rfind('/'):])
                else:
                    RAA['bild'].append(url)
        #new params
        RAA['skydd'] = ''
        xmlTag = dom.getElementsByTagName('rdf:Description')
        for x in xmlTag:
            if len(x.getElementsByTagName('ns5:type'))>0:
                    if x.getElementsByTagName('ns5:type')[0].childNodes[0].data.strip() == u'Antikvarisk bed�mning':
                            RAA['skydd'] = x.getElementsByTagName('ns5:spec')[0].childNodes[0].data.strip()
    #
    @staticmethod
    def getSignum(objektid, runDict):
        '''Finds the corresponding signum (possibly multiple) from the nycklar page. Returns (signum, number of hits).
        would be more efficient to do this using datastore but that misses potential updates.'''
        found = False
        signum =None
        filename = u'http://sv.wikipedia.org/w/api.php?action=query&prop=revisions&format=xml&rvprop=content&rvlimit=1&titles=Anv%C3%A4ndare%3ALokal%20Profil%2Fnycklar%2Fsignum'
        try:
            fil = urllib2.urlopen(filename)
        except HTTPError, e:
            runDict['problem'] = (u'signum-problem: httpError f�r %s' % filename, u'Felkod: %d' % e.code)
            return None
        except URLError, e:
            runDict['problem'] = (u'signum-problem: urlError f�r %s' % filename, cgi.escape(e.reason[0]))
            return None
        else:
            dom = parse(fil)
            fil.close()
            del fil
            contents = dom.getElementsByTagName('rev')[0].childNodes[0].data
            lines = contents.split('\n')
            for l in lines:
                if l.startswith('| '+objektid):
                    e = l.split(' = ')
                    num = e[0].strip()[2:]
                    signum = e[1].strip()
                    found = True
                    break
            #deal with possibility of multiple signum
            if found:
                signum = (signum, len(signum.split(' , ')))
            else:
                signum = ('', 0)
            return signum
    #
    @staticmethod
    def getSRDB(runDict, signum):
        '''Gets SRDB info from nycklar page'''
        if len(signum)==0: #if signum is blank then just stop
            runDict['results'] = False
            return
        filename = u'http://sv.wikipedia.org/w/api.php?action=query&prop=revisions&format=xml&rvprop=content&rvlimit=1&titles=Anv%C3%A4ndare%3ALokal%20Profil%2Fnycklar%2FSRDB'
        try:
            fil = urllib2.urlopen(filename)
        except HTTPError, e:
            runDict['problem'] = (u'SRDB-problem: httpError f�r %s' % filename, u'Felkod: %d' % e.code)
            return None
        except URLError, e:
            runDict['problem'] = (u'SRDB-problem: urlError f�r %s' % filename, cgi.escape(e.reason[0]))
            return None
        else:
            dom = parse(fil)
            fil.close()
            del fil
            contents = dom.getElementsByTagName('rev')[0].childNodes[0].data
            lines = contents.split('\n')
            line=''
            #find the matching line
            for i in range(0,len(lines)):
                if lines[i].startswith('| '+signum):
                    while not ' = ' in lines[i]:                       #since some signums have multiple designations and description with the last one
                        i += 1
                    line=lines[i]
                    break
            #freeing up memory
            del dom, contents, lines
            #if a matching line was found
            if not len(line) == 0:
                runDict['results'] = True
                runinfo = {'plats': 'runPlats',
                           'placering': 'runPlacering',
                           'stil' : 'runStil',
                           'ristare': 'runRistare',
                           'datering' : 'runDatering',
                           'bild' : 'runBild'}
                for key in runinfo.keys():
                    startpos = line.find('|'+key+'=')
                    if startpos>0:                   #i.e. found
                        startparse = startpos+len(key)+2
                        endpos = line.find('|', startparse)
                        while '{{' in line[startparse:endpos]:        #if template then need to find real pipe
                            startparse = line.find('}}',startparse)+2
                            endpos = line.find('|', startparse)       #first pipe after end of templates
                        if endpos < 0:
                            endpos = len(line)-2                      #last parameter does not have pipe
                        runDict[runinfo[key]] = line[startpos+len(key)+2:endpos]
                    else:
                        runDict[runinfo[key]] = ''
                #special formating for images
                if len(runDict['runBild']) >0:
                    runDict['runBild'] = runDict['runBild'].split(', ')
                #special formating for dates
                if len(runDict['runDatering']) >0:
                    if runDict['runDatering'].startswith('V/M'):
                        runDict['runDatering'] = '[[Vikingatida|V]]/[[Medeltida|M]]'+runDict['runDatering'][3:]
                    elif runDict['runDatering'].startswith('U/V'):
                        runDict['runDatering'] = '[[Urnordiska|U]]/[[Vikingatida|V]]'+runDict['runDatering'][3:]
                    elif runDict['runDatering'].startswith('V'):
                        runDict['runDatering'] = '[[Vikingatida|V]]'+runDict['runDatering'][1:]
                    elif runDict['runDatering'].startswith('M'):
                        runDict['runDatering'] = '[[Medeltida|M]]'+runDict['runDatering'][1:]
                    elif runDict['runDatering'].startswith('U'):
                        runDict['runDatering'] = '[[Urnordiska|U]]'+runDict['runDatering'][1:]
                    while ' m ' in runDict['runDatering']:
                        pos = runDict['runDatering'].find(' m ')
                        runDict['runDatering'] = runDict['runDatering'][:pos]+' mitten av '+runDict['runDatering'][pos+3:]
                    while ' s ' in runDict['runDatering']:
                        pos = runDict['runDatering'].find(' s ')
                        runDict['runDatering'] = runDict['runDatering'][:pos]+' slutet av '+runDict['runDatering'][pos+3:]
                    while ' b ' in runDict['runDatering']:
                        pos = runDict['runDatering'].find(' b ')
                        runDict['runDatering'] = runDict['runDatering'][:pos]+u' b�rjan av '+runDict['runDatering'][pos+3:]
            else:                           #if no match found
                runDict['results'] = False
                return
    #
    @staticmethod
    def commonsPics(RAA):
        u'''kollar om det finns uppm�rkta bilder p� Commons'''
        filename = u'https://commons.wikimedia.org/w/api.php?action=query&list=exturlusage&format=xml&euprop=title&euquery=kulturarvsdata.se/raa/fmi/html/%s&eunamespace=6&euoffset=0&eulimit=5' % RAA['objektid']
        try:
            fil = urllib2.urlopen(filename)
        except HTTPError, e:
            RAA['problem'] = (u'commons-problem: httpError f�r %s' % filename, u'Felkod: %d' % e.code)
            return None
        except URLError, e:
            RAA['problem'] = (u'commons-problem: urlError f�r %s' % filename, cgi.escape(e.reason[0]))
            return None
        else:
            dom = parse(fil)
            fil.close()
            del fil
            items = dom.getElementsByTagName('eu')
            #antal tr�ffar
            num = len(items)
            if not num == 0:                   #finns det n�gra alls? 
                RAA['bildCommons'] = items[0].attributes['title'].value[5:]
            return num
    #
    @staticmethod
    def createTemplate(RAA, runDict):
        txt =  u'{{Infobox fornminne\n'
        txt += u' | namn        = %s\n' % RAA['namn']
        txt += u' | typ         = %s\n' % RAA['typ']
        txt += u' | undertyp    = \n'
        txt += u' | bild        = '
        if 'bildCommons' in RAA.keys():
            txt += RAA['bildCommons']
        txt += '\n'
        txt += u' | bild_text   = \n'
        if 'alt_namn' in RAA.keys():
            txt += u'<!-- Beteckningar -->\n'
            txt += u' | alternativt_namn = %s\n' % RAA['alt_namn']
        txt += u'<!-- Geo -->\n'
        txt += u' | land        = [[Sverige]]\n'
        txt += u' | landskap    = [[{{safesubst:Anv�ndare:Lokal Profil/nycklar/landskap|%s}}]]\n' % RAA['landskap']
        txt += u' | l�n         = [[{{safesubst:Anv�ndare:Lokal Profil/nycklar/l�n|%s}}|%s]]\n' %(RAA['lan'],RAA['lanName'])
        txt += u' | kommun      = [[{{safesubst:Anv�ndare:Lokal Profil/nycklar/kommuner|%s}}|%s]]\n' %(RAA['kommun'],RAA['kommunName'])
        txt += u' | socken      = [[{{safesubst:Anv�ndare:Lokal Profil/nycklar/socknar|%s}}|%s]] <!--ATA %s-->\n' %(RAA['socken'], RAA['sockenName'], RAA['socken'])
        txt += u' | plats       = '
        if runDict['results']:
            txt += runDict['runPlats']
        txt += u'\n'
        txt += u' | coord       = '
        if ('latitude' in RAA.keys()) and (len(RAA['latitude'])>0):
            txt += u'{{coord|%s|%s|display=inline,title|type:landmark}}' % (RAA['latitude'], RAA['longitude'])
        txt +=u'\n'
        txt += u' | h�jdl�ge    = \n'
        if runDict['results']:
            txt += u' | nu_plats    = %s\n' % runDict['runPlacering']
        if RAA['typ'] == 'Runristning':
            txt += u'<!-- Runspecifikt -->\n'
            txt += u' | signum      = '
            if 'signum' in runDict.keys():
                txt += runDict['signum']
            txt += '\n'
            if runDict['results']:
                txt += u' | ristare     = %s\n' % runDict['runRistare']
                txt += u' | runstil     = %s\n' % runDict['runStil']
            else:
                txt += u' | ristare     = \n'
                txt += u' | runstil     = \n'
            txt += u' | rungrupp    = \n'
        txt += u'<!-- Allm�n info -->\n'
        txt += u' | tillkomsttid= '
        if runDict['results']:
            txt += runDict['runDatering']
        txt += u'\n'
        txt += u' | antal       = \n'
        txt += u' | del_av      = \n'
        txt += u' | inneh�ller  = \n'
        txt += u'<!-- Skyddsinfo -->\n'
        txt += u' | skydd       = %s\n' % RAA['skydd']
        txt += u' | skydd_nr    = {{RA�-nummer|%s|%s}}\n' % (RAA['raa-nr'], RAA['objektid'])
        txt += u' | fotnoter    = Information fr�n [[FMIS]]'
        if runDict['results']:
            txt += u' samt [http://www.nordiska.uu.se/forskn/samnord.htm Samnordisk runtextdatabas]'
        txt +=u'.\n'
        txt += u'}}\n'
        return txt
#
class Format:
    @staticmethod
    def recoverList(string):
        '''recovers a list from an urlencoded payload.'''
        lista = string[1:].split('|')
        return lista
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

app = webapp2.WSGIApplication([('/fmis/', MainPage),
                               ('/fmis/result', Fornminne)],
                              debug=True)
