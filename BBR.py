# -*- coding: UTF-8  -*-
##
##Including andring seems to make me run out of memory
##Make sure problems are presented in a sensible way even on success
##
import cgi
import webapp2
import urllib2, urllib
from urllib2 import URLError, HTTPError
from xml.dom.minidom import parse
#
class MainPage(webapp2.RequestHandler):
    def get(self):
        idnr=self.request.get('idnr')
        reason=self.request.get('reason')
        self.response.out.write(Format.header(u'Ange BBR id'))
        if not len(reason) == 0:
            self.response.out.write(reason)
        else:
            self.response.out.write(u'''Ange ett 14-siffriga id. <br/>''')
        self.response.out.write(u'''
              <form action="filter" method="post">
                <div><input value="%s" name="idnr"></div>
                <div><input type=radio name="typ" value="bbra" checked> Anläggning
                     <input type=radio name="typ" value="bbrb"> Byggnad</div>
                <div><input type="submit" value="Ange id och typ"></div>
              </form>''' % idnr)
        self.response.out.write(u'''
              <i>För att hitta rätt id är den enklaste metoden att gå till presentationssida hos bebyggelseregistret.<br/>
                 Url:en för presentationssida innehåller det 14-siffriga ID numret samt anger om presentationen är för en byggnad, anläggning eller miljö.<br/>
              </i>''')
        self.response.out.write(Format.footer())
#
class Filter(webapp2.RequestHandler):
    def post(self):
        idnr=self.request.get('idnr')
        typ=self.request.get('typ')
        if (not len(idnr) == 14) or (not idnr.isdigit()):
            self.redirect('/bbr/?' + Format.urlencode({'idnr': idnr, 'reason': u'Sorry men "%s" är inte ett 14-siffrigt nummer. Försök igen.' % idnr}), abort=True)
        elif typ == 'bbra':
            self.redirect('/bbr/bbra?' + urllib.urlencode({'idnr': idnr}), abort=True)
        elif typ =='bbrb':
            self.redirect('/bbr/bbrb?' + urllib.urlencode({'idnr': idnr}), abort=True)
        else:
            self.response.out.write(u'Felaktig typ: %s' % typ)
#
class BBRA(webapp2.RequestHandler):
    def get(self):
        run = True
        idnr=self.request.get('idnr')
        path ='bbr' #changes if page live at /bbra/ rather than /bbr/
        objektid = idnr
        bbraDict = {'id' : idnr}
        try:
            fil = urllib2.urlopen('http://kulturarvsdata.se/raa/%s/%s' %(path, cgi.escape(objektid)))
        except HTTPError, e:
            path = 'bbra'
            try:
                fil = urllib2.urlopen('http://kulturarvsdata.se/raa/%s/%s' %(path, cgi.escape(objektid)))
            except HTTPError, e:
                run = False
                self.response.out.write(Format.header(u'Problem med BBR id: %s' %objektid))
                self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyvärr inte leverera datan. Säker på att du angivit rätt objektid?<br/>')
                self.response.out.write(u'Felkod: %d<br/>' % e.code)
                self.response.out.write(Format.footer())
        except URLError, e: 
            run = False
            self.response.out.write(Format.header(u'Problem med BBR id: %s' %objektid))
            self.response.out.write(cgi.escape(e.reason[0])+'<br/>')
            self.response.out.write(Format.footer())
        else:
            #convert to xml:
            dom = parse(fil)
            #close file because we dont need it anymore:
            fil.close()
            del fil
            bbraDict['problem'] = []
            bbraDict['kyrka'] = False
            if not BBRA.bbraParser(dom, bbraDict):
                run = False
                if bbraDict['typ'] == u'bbrb':
                    typ = u'byggnad'
                elif bbraDict['typ'] == u'bbrm':
                    typ = u'miljö'
                else:
                    typ = bbraDict['typ']
                self.redirect('/bbr/?' + Format.urlencode({'idnr': idnr, 'reason': u'Du angav att detta var en anläggning men numret är för en %s. Försök igen.</br>Andra problem: %s' % (typ, bbraDict['problem'])}), abort=True)
            elif len(bbraDict['problem'])>0:
                run = True
                self.response.out.write(Format.header(u'Problem med BBR id: %s' %objektid))
                self.response.out.write(u'Something went wrong. Therefore the template below should be used with caution and only after having considered the error messages below.<br/>')
                self.response.out.write(u'For id %s:<br/>' %objektid)
                for p in bbraDict['problem']:
                    self.response.out.write(cgi.escape(u'*"%s" with value <%s>' % (p[0],p[1]))+'<br/>')
                self.response.out.write(u'If you think this error arose by misstake then please complain to Lokal_Profil (including the text above)<br/><hr><br/>')
                #self.response.out.write(Format.footer())
        if run:
            bbraDict['path'] = path
            if len(bbraDict['bbrb'])>0:
                bbraDict['commonsPics'] = BBR.commonsPics(bbraDict, [(bbraDict['id'],bbraDict['path'])]+bbraDict['bbrb'])
            else:
                bbraDict['commonsPics'] = BBR.commonsPics(bbraDict, [(bbraDict['id'],bbraDict['path'])])
            if bbraDict['commonsPics'] == None:
                response  = Format.header(u'Problem med BBR id: %s' %objektid)
                response += u'Something went wrong. Please complain to Lokal_Profil stating the following:<br/>For id %s:<br/>' %objektid
                for p in bbraDict['problem']:
                    response += cgi.escape(u'*"%s" with value <%s>' % (p[0],p[1]))+'<br/>'
                response += Format.footer()
                return self.response.out.write(response)
            #All seems to have worked
            self.response.out.write(Format.header(u'Resultat för BBR id: %s' %objektid))
            self.response.out.write(u'Anläggningspresentation hos BBR: <a href="http://kulturarvsdata.se/raa/%s/html/%s" target="_blank">%s</a><br/>' %(path, objektid, objektid))
            if bbraDict['commonsPics'] > 0:
                picIds = bbraDict['id']
                if len(bbraDict['bbrb']) > 0:
                    # build a regexp like /(21000001648601|10039701480002)/
                    picIds = u'/(%s' % picIds
                    for b in bbraDict['bbrb']:
                        picIds += u'|%s' % b[0]
                    picIds += u')/'
                self.response.out.write(u'För fler commonsbilder se <a href="https://commons.wikimedia.org/w/index.php?title=Special:Search&search=insource:%s&ns0=1&ns6=1&ns14=1&redirs=1" target="_blank">här</a> (minst %d bilder)<br/>' % (picIds, int(bbraDict['commonsPics'])) )
            if len(bbraDict['bbrb'])>1:
                self.response.out.write(u'<b>Notera!</b> Denna anläggning innehåller %d enskilda byggnader vilket har gjort att information om arkitekt, byggnadsstart etc. inte kunnat hämtas.<br/>Koordinaterna som anges är mittpunkten för anläggningen (viktad för antalet byggnader)<br/>' % len(bbraDict['bbrb']))
            elif len(bbraDict['bbrb'])==0:
                self.response.out.write(u'<b>Notera!</b> Verktyget hittade inga byggnader som ingick i denna anläggningen. Verifiera gärna manuellt att detta stämmer.<br/>')
            if len(bbraDict['skydd']) == 0:
                self.response.out.write(u'<b>Verktyget hittade inget skydd för anläggningen</b>. Verifiera gärna manuellt att detta stämmer. Om inte så flytta upp informationen från <TT>bbr</TT>-parametern till <TT>skydd_nr</TT>-parametern samt fyll i övrig skyddsinformation.</br>')
            #Start writing template
            self.response.out.write(u'<br/>Kopiera in följande i artikeln:<br/><pre>')
            self.response.out.write(cgi.escape(BBR.createTemplate(bbraDict)))
            self.response.out.write('</pre>')
            self.response.out.write(Format.footer())
        #done
    #
    @staticmethod
    def bbraParser(dom, bbraDict):
        #tags to get
        tagDict = {'namn': ('ns5:itemTitle', None),
                   'typ' : ('ns5:serviceName', None),
                   'reg-nr' : ('ns5:cadastralUnit', None),
                   'lan' : ('ns6:county', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/county#'),
                   'lanName' : ('ns5:countyName', None),
                   'kommun' : ('ns6:municipality', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/municipality#'),
                   'kommunName' : ('ns5:municipalityName', None)}
        #
        for tag in tagDict.keys():
            xmlTag = dom.getElementsByTagName(tagDict[tag][0])
            if not len(xmlTag) ==0:
                if tagDict[tag][1] == None:
                    bbraDict[tag] = xmlTag[0].childNodes[0].data.strip('"')
                else:
                    bbraDict[tag] = xmlTag[0].attributes[tagDict[tag][1]].value[len(tagDict[tag][2]):]
            else:
                bbraDict[tag] = ''               #Makes template building easier
        #verify that this is bbra and not bbrb/bbrm
        if not bbraDict['typ'] == 'bbra':
            bbraDict['problem'].append((u'Not right type', bbraDict['typ']))
            return False
        #tweak for name
        bbraDict['namn'] = bbraDict['namn'].title()
        #do categories searately
        xmlTag = dom.getElementsByTagName('ns5:itemClassName')
        if not len(xmlTag) == 0:
            bbraDict['kategorier'] = []
            for x in xmlTag:
                kat = x.childNodes[0].data.strip()
                if not kat in bbraDict['kategorier']:
                    bbraDict['kategorier'].append(kat)
        ##do skydd separat
        bbraDict['skydd'] = []
        xmlTag = dom.getElementsByTagName('rdf:Description')
        for x in xmlTag:
            if len(x.getElementsByTagName('ns5:contextLabel'))>0 and x.getElementsByTagName('ns5:contextType')[0].attributes[ 'rdf:resource'].value=='http://kulturarvsdata.se/resurser/ContextType#explore': #skydd from contextLabel
                skydd = x.getElementsByTagName('ns5:contextLabel')[0].childNodes[0].data.strip()
                if len(x.getElementsByTagName('ns5:fromTime'))>0:
                    fromTime = x.getElementsByTagName('ns5:fromTime')[0].childNodes[0].data.strip()
                    toTime = x.getElementsByTagName('ns5:toTime')[0].childNodes[0].data.strip()
                else:
                    fromTime = toTime = u'01939' # 0 to sort correctly
                bbraDict['skydd'].append([fromTime,toTime,skydd])
        #Now check and format
        if not len(bbraDict['skydd'])==0:
            if not BBR.formatSkydd(bbraDict):
                return True #return early if problem encountered
        ##do bbrb's searately
        xmlTag = dom.getElementsByTagName('ns5:hasPart')
        bbraDict['bbrb'] = []# so antal=len(bbraDict['bbrb'])
        if not len(xmlTag) == 0:
            for x in xmlTag:
                url = x.attributes['rdf:resource'].value.strip()
                if url.startswith('http://kulturarvsdata.se/raa/bbr/'):
                    bbraDict['bbrb'].append((url.strip('http://kulturarvsdata.se/raa/bbr/'),'bbr'))
                else:
                    bbraDict['bbrb'].append((url.strip('http://kulturarvsdata.se/raa/bbrb/'),'bbrb'))
            #memory seems to be an issue so kill dom
            del dom, x
            #combine coords
            latitude  = 0
            longitude = 0
            counter   = 0
            for bbrb in bbraDict['bbrb']:
                coord = BBRA.bbrbCoords(bbrb[0],bbrb[1],bbraDict)
                if (not coord == None) and (len(coord)>0): #if not problem or no coord
                    latitude  += float(coord[0])
                    longitude += float(coord[1])
                    counter   += 1
                elif coord == None: #if problem (was made nicer so as not to kill everything)
                    return True #return early if problem encountered
                    #return None
            if not counter == 0:
                bbraDict['latitude']  = str(latitude/float(counter))[0:8]
                bbraDict['longitude'] = str(longitude/float(counter))[0:8]
            else:
                bbraDict['latitude'] = bbraDict['longitude'] = ''
            #more info from
            if len(bbraDict['bbrb'])==1:                      #bbrb if anlaggning is constructed by a sole building then we can get info from that one
                bbrbTags = ('stift', 'forsamling', 'arkitekt', 'arkitekt_etikett', 'byggherre', 'fardig', 'byggstart', 'andring')
            else:                                             #otherwise just get stift, forsamling which should always be the same
                bbrbTags = ('stift', 'forsamling')
            urlb='http://kulturarvsdata.se/raa/%s/%s' % (bbraDict['bbrb'][0][1],bbraDict['bbrb'][0][0])
            try:
                filb = urllib2.urlopen(urlb)
            except HTTPError, e:
                bbraDict['problem'].append((u'bbrb-problem: httpError för %s' % url, u'Felkod: %d' % e.code))
                return True
            except URLError, e:
                bbraDict['problem'].append((u'bbrb-problem: urlError för %s' % url, cgi.escape(e.reason[0])))
                return True
            else:
                bbrbDict = {}
                #convert to xml:
                domb = parse(filb)
                #close file because we dont need it anymore:
                filb.close()
                del filb
                BBRB.bbrbParser(domb, bbrbDict)
                for tag in bbrbTags:
                    if tag in bbrbDict.keys():
                        bbraDict[tag] = bbrbDict[tag]
        return True
    #
    @staticmethod
    def bbrbCoords(idnr, path, bbrDict):
        url='http://kulturarvsdata.se/raa/%s/%s' % (path, idnr)
        try:
            fil = urllib2.urlopen(url)
        except HTTPError, e:
            bbrDict['problem'].append((u'koordinatproblem: httpError för %s' % url, u'Felkod: %d' % e.code))
            return None
        except URLError, e:
            bbrDict['problem'].append((u'koordinatproblem: urlError för %s' % url, cgi.escape(e.reason[0])))
            return None
        else:
            #convert to xml:
            dom = parse(fil)
            #close file because we dont need it anymore:
            fil.close()
            del fil
            #get coordinates
            xmlTag = dom.getElementsByTagName('georss:where')
            if not len(xmlTag) == 0:
                xmlTag = xmlTag[0].childNodes[0].childNodes[0]
                cs = xmlTag.attributes['cs'].value
                #dec = xmlTag.attributes['decimal'].value
                coords = xmlTag.childNodes[0].data.split(cs)
                if len(coords) == 2:
                    latitude =coords[1]
                    longitude =coords[0]
                    return (latitude, longitude)
                else:
                    bbrDict['problem'].append((u'koordinatproblem: coord was not point for %s' % url, coords))
                    return None
            return ''
#
class BBRB(webapp2.RequestHandler):
    def get(self):
        run = True
        idnr=self.request.get('idnr')
        path ='bbr' #changes if page live at /bbra/ rather than /bbr/
        objektid = idnr
        bbrbDict = {'id' : idnr}
        try:
            fil = urllib2.urlopen('http://kulturarvsdata.se/raa/%s/%s' %(path, cgi.escape(objektid)))
        except HTTPError, e:
            path = 'bbrb'
            try:
                fil = urllib2.urlopen('http://kulturarvsdata.se/raa/%s/%s' %(path, cgi.escape(objektid)))
            except HTTPError, e:
                run = False
                self.response.out.write(Format.header(u'Problem med BBR id: %s' %objektid))
                self.response.out.write(u'Servern hos kulturarvsdata.se kunde tyvärr inte leverera datan. Säker på att du angivit rätt objektid?<br/>')
                self.response.out.write(u'Felkod: %d<br/>' % e.code)
                self.response.out.write(Format.footer())
        except URLError, e:
            run = False
            self.response.out.write(Format.header(u'Problem med BBR id: %s' %objektid))
            self.response.out.write(cgi.escape(e.reason[0])+'<br/>')
            self.response.out.write(Format.footer())
        else:
            #convert to xml:
            dom = parse(fil)
            #close file because we dont need it anymore:
            fil.close()
            del fil
            bbrbDict['problem'] = []
            bbrbDict['kyrka'] = False
            if not BBRB.bbrbParser(dom, bbrbDict):
                run = False
                if bbrbDict['typ'] == u'bbra':
                    typ = u'anläggning'
                elif bbrbDict['typ'] == u'bbrm':
                    typ = u'miljö'
                else:
                    typ = bbrbDict['typ']
                self.redirect('/bbr/?' + Format.urlencode({'idnr': idnr, 'reason': u'Du angav att detta var en byggnad men numret är för en %s. Försök igen.' % typ}), abort=True)
            elif len(bbrbDict['problem'])>0:
                run = False
                self.response.out.write(Format.header(u'Problem med BBR id: %s' %objektid))
                self.response.out.write(u'Something went wrong. Please complain to Lokal_Profil stating the following:<br/>')
                self.response.out.write(u'For id %s:<br/>' %objektid)
                for p in bbrbDict['problem']:
                    self.response.out.write(cgi.escape(u'*"%s" with value <%s>' % (p[0],p[1]))+'<br/>')
                self.response.out.write(Format.footer())
        if run:
            bbrbDict['path'] = path
            bbrbDict['commonsPics'] = BBR.commonsPics(bbrbDict, [(bbrbDict['id'],bbrbDict['path'])])
            if bbrbDict['commonsPics'] == None:
                response  = Format.header(u'Problem med BBR id: %s' %objektid)
                response += u'Something went wrong. Please complain to Lokal_Profil stating the following:<br/>For id %s:<br/>' %objektid
                for p in bbrbDict['problem']:
                    response += cgi.escape(u'*"%s" with value <%s>' % (p[0],p[1]))+'<br/>'
                response += Format.footer()
                return self.response.out.write(response)
            #everything seems to have worked
            self.response.out.write(Format.header(u'Resultat för BBR id: %s' %objektid))
            self.response.out.write(u'Byggnadspresentation hos BBR: <a href="http://kulturarvsdata.se/raa/%s/html/%s" target="_blank">%s</a><br/>' %(path, objektid, objektid))
            if bbrbDict['commonsPics'] >0:
                self.response.out.write(u'För fler commonsbilder se <a href="https://commons.wikimedia.org/w/index.php?title=Special:Search&search=insource:%s&ns0=1&ns6=1&ns14=1&redirs=1" target="_blank">här</a> (minst %d bilder).<br/>' % (bbrbDict['id'], int(bbrbDict['commonsPics'])) )
            self.response.out.write(u'Det kan också finnas bilder uppmärkta med anläggningsid <a href="https://commons.wikimedia.org/w/index.php?title=Special:Search&search=insource:%s&ns0=1&ns6=1&ns14=1&redirs=1" target="_blank">på Commons</a>.<br/>' % bbrbDict['bbra'][0] )
            if ('arkitekt' in bbrbDict.keys()) or ('byggherre' in bbrbDict.keys()):
                self.response.out.write(u'<b>Notera!</b> Enbart den första upphovsmannen (byggherre/arkitekt) kan hittas av detta verktyg.<br/>')
            if 'fardig' in bbrbDict.keys():
                self.response.out.write(u'<b>Notera!</b> Enbart det första "nybyggnads"-datumet används.<br/>')
            if len(bbrbDict['skydd']) == 0:
                self.response.out.write(u'<b>Verktyget hittade inget skydd för byggnaden</b>. Verifiera gärna manuellt att detta stämmer. Om inte så flytta upp informationen från <TT>bbr</TT>-parametern till <TT>skydd_nr</TT>-parametern samt fyll i övrig skyddsinformation.</br>')
            #Start writing template
            self.response.out.write(u'<br/>Kopiera in följande i artikeln:<br/><pre>')
            self.response.out.write(cgi.escape(BBR.createTemplate(bbrbDict)))
            self.response.out.write('</pre>')
            self.response.out.write(Format.footer())
        #done
    #
    @staticmethod
    def bbrbParser(dom, bbrbDict):
        #tags to get
        tagDict = {'namn': ('ns5:itemTitle', None),
                   'typ' : ('ns5:serviceName', None),
                   'reg-nr' : ('pres:idLabel', None),
                   'lan' : ('ns6:county', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/county#'),
                   'lanName' : ('ns5:countyName', None),
                   'kommun' : ('ns6:municipality', 'rdf:resource', 'http://kulturarvsdata.se/resurser/aukt/geo/municipality#'),
                   'kommunName' : ('ns5:municipalityName', None)}
        #
        for tag in tagDict.keys():
            xmlTag = dom.getElementsByTagName(tagDict[tag][0])
            if not len(xmlTag) ==0:
                if tagDict[tag][1] == None:
                    bbrbDict[tag] = xmlTag[0].childNodes[0].data.strip('"')
                else:
                    bbrbDict[tag] = xmlTag[0].attributes[tagDict[tag][1]].value[len(tagDict[tag][2]):]
            else:
                bbrbDict[tag] = ''               #Makes template building easier
        #verify that this is bbra and not bbrb/bbrm
        if not bbrbDict['typ'] == 'bbrb':
            bbrbDict['problem'].append((u'Not right type', bbrbDict['typ']))
            return False
        #forsamling o stift
        bbrbDict['forsamling'] = bbrbDict['stift'] = ''
        xmlTag = dom.getElementsByTagName('ns5:placeName')
        for x in xmlTag:
            value = x.childNodes[0].data.strip('')
            if value.startswith(u'Församling: '):
                bbrbDict['forsamling'] = value[len(u'Församling: '):]
            elif value.startswith('Frsamling: '): #for backwards compatibility
                bbrbDict['forsamling'] = value[len('Frsamling: '):]
            elif value.startswith('Stift: '):
                bbrbDict['stift'] = value[len('Stift: '):]
        #do bbra searately
        xmlTag = dom.getElementsByTagName('ns5:isPartOf')
        if not len(xmlTag) == 0:
            url = xmlTag[0].attributes['rdf:resource'].value.strip()
            if url.startswith('http://kulturarvsdata.se/raa/bbr/'):
                bbrbDict['bbra'] = (url.strip('http://kulturarvsdata.se/raa/bbr/'),'bbr')
            else:
                bbrbDict['bbrb'] = (url.strip('http://kulturarvsdata.se/raa/bbra/'),'bbra')
        #tweak for name and reg-nr
        bbrbDict['namn'] = bbrbDict['namn'].title()
        bbrbDict['reg-nr'] = bbrbDict['reg-nr'].title()
        #get coordinates
        xmlTag = dom.getElementsByTagName('georss:where')
        if not len(xmlTag) == 0:
            xmlTag = xmlTag[0].childNodes[0].childNodes[0]
            cs = xmlTag.attributes['cs'].value
            #dec = xmlTag.attributes['decimal'].value
            coords = xmlTag.childNodes[0].data.split(cs)
            if len(coords) == 2:
                bbrbDict['latitude']  = coords[1]
                bbrbDict['longitude'] = coords[0]
            else:
                bbrbDict['problem'].append((u'koordinatproblem: coord was not a point for %s' % url, coords))
                return
        #do categories searately
        xmlTag = dom.getElementsByTagName('ns5:itemClassName')
        if not len(xmlTag) == 0:
            bbrbDict['kategorier'] = []
            for x in xmlTag:
                kat = x.childNodes[0].data.strip()
                if not kat in bbrbDict['kategorier']:
                    bbrbDict['kategorier'].append(kat)
        ##do skydd/nybbygnad separat
        bbrbDict['skydd'] = []
        bbrbDict['andring'] = []
        skyddsStart = (
            u'3 kap. kulturminneslagen', u'Byggnadsminne (BM) 3 kap. KML',
            u'4 kap. kulturminneslagen', u'Kyrkligt kulturminne. 4 kap. KML',
            u'Förordning (1988:1229)', u'Statligt byggnadsminne (SBM). Förordning (2013:558)',
            u'Hävt ')
        xmlTag = dom.getElementsByTagName('rdf:Description')
        for x in xmlTag:
            if len(x.getElementsByTagName('ns5:contextLabel'))>0: #if it has a contextLabel
                value = x.getElementsByTagName('ns5:contextLabel')[0].childNodes[0].data.strip()
                if value.startswith(skyddsStart): #if a skydd
                    if len(x.getElementsByTagName('ns5:fromTime'))>0:
                        fromTime = x.getElementsByTagName('ns5:fromTime')[0].childNodes[0].data.strip()
                        toTime = x.getElementsByTagName('ns5:toTime')[0].childNodes[0].data.strip()
                    else:
                        fromTime = toTime = u'01939' # 0 to sort correctly
                    bbrbDict['skydd'].append([fromTime,toTime,value])
                elif value.startswith(u'Nybyggnad'):
                    if 'fardig' not in bbrbDict.keys(): # only add the first one
                        if len(x.getElementsByTagName('ns5:fromTime'))>0:
                            fromTime = x.getElementsByTagName('ns5:fromTime')[0].childNodes[0].data.strip()
                            #toTime is not guaranteed to exist
                            if len(x.getElementsByTagName('ns5:toTime'))>0: #toTime isn't guaranteed to exist
                                toTime    = x.getElementsByTagName('ns5:toTime')[0].childNodes[0].data.strip()
                                dates = Format.dateInterpreter(fromTime,toTime)
                            else:
                                dates = (fromTime,)
                            if len(dates)==1:
                                bbrbDict['fardig'] = dates[0]
                            else:
                                bbrbDict['byggstart'] = dates[0]
                                bbrbDict['fardig'] = dates[1]
                        if len(x.getElementsByTagName('ns7:fullName'))>0:
                            if x.getElementsByTagName('ns7:fullName')[0].firstChild:
                                byggNamn  = x.getElementsByTagName('ns7:fullName')[0].childNodes[0].data.strip()
                                byggTitle = x.getElementsByTagName('ns7:title')[0].childNodes[0].data.strip()
                                if byggTitle == u'Arkitekt':
                                    bbrbDict['arkitekt'] = byggNamn
                                elif byggTitle == u'Byggherre':
                                    bbrbDict['byggherre'] = byggNamn
                                else:
                                    bbrbDict['arkitekt'] = byggNamn
                                    bbrbDict['arkitekt_etikett'] = byggTitle
                elif value.startswith(u'Ändring - '):
                    andrad = value[len(u'Ändring - '):]
                    if len(x.getElementsByTagName('ns5:fromTime'))>0:
                        fromTime = x.getElementsByTagName('ns5:fromTime')[0].childNodes[0].data.strip()
                        if len(x.getElementsByTagName('ns5:toTime'))>0:               #for some reason toTime isn't guaranteed
                            toTime = x.getElementsByTagName('ns5:toTime')[0].childNodes[0].data.strip()
                            dates = Format.dateInterpreter(fromTime,toTime,swe=False) #swe false due to sorting being needed
                            bbrbDict['andring'].append([dates[0],andrad])
                        else:
                            bbrbDict['andring'].append([fromTime,andrad])
                    else:
                        bbrbDict['andring'].append(['',andrad])
        #Memory seems to be an issue so kill dom
        del dom, x
        #Now check and format skydd
        if not len(bbrbDict['skydd'])==0:
            BBR.formatSkydd(bbrbDict)
        #Now format andring
        bbrbDict['andring'].sort()
        for a in bbrbDict['andring']:
            a[0] = Format.sweDate(a[0])
        return True
#
#GENERIC METHODS
class BBR():
    @staticmethod
    def formatSkydd(bbrDict):
        '''verifies that toTime = fromTime and formats the skydd-object'''
        #require toTime and fromTime to be the same, change toTime to the next fromTime
        bbrDict['skydd'].sort()
        i = 0
        while i < (len(bbrDict['skydd'])-1):
            s=  bbrDict['skydd'][i]
            if not s[0] == s[1]:
                bbrDict['problem'].append((u'fromTime not same as toTime', '%s != %s' % (s[0],s[1])))
                return False
            else:
                while (i < (len(bbrDict['skydd'])-1)) and (s[2] == bbrDict['skydd'][i+1][2]): #if same skydd is repeated then remove the latter
                    del bbrDict['skydd'][i+1]
                if i == (len(bbrDict['skydd'])-1): #if last was removed due to the above
                    s[1] = ''
                else:
                    s[1] = bbrDict['skydd'][i+1][0]     #change toTime to the next fromTime
                s[2] = BBR.skyddmatch(s[2],bbrDict)       #identify skydd per string
                i += 1
        if i == (len(bbrDict['skydd'])-1):
            s=  bbrDict['skydd'][i]
            if not s[0] == s[1]:
                bbrDict['problem'].append((u'fromTime not same as toTime', '%s != %s' % (s[0],s[1])))
                return False
            s[1] = '' #remove toTime
            s[2] = BBR.skyddmatch(s[2],bbrDict)
        if bbrDict['skydd'][len(bbrDict['skydd'])-1][2] == 'cancled': #removed anny "Hävda"
            del bbrDict['skydd'][len(bbrDict['skydd'])-1]
        bbrDict['skydd'].sort(reverse=True)
        for s in bbrDict['skydd']:
            s[1] = Format.sweDate(s[1])
            if s[0] == '01939':
                    s[0] = u'före 1939'
                    if not s[2] == u'Kyrkligt kulturminne':
                        bbrDict['problem'].append((u'Skyddsstart saknas för icke-kyrka', '%s' % (s[2])))
                        return False
            else:
                s[0] = Format.sweDate(s[0])
        return True
    #
    @staticmethod
    def skyddmatch(text, bbrDict):
        '''matches the skydd string to a type of skydd'''
        if text == u'3 kap. kulturminneslagen.  Byggnadsminne' or text == u'Byggnadsminne (BM) 3 kap. KML':
            return u'Enskilt byggnadsminne'
        elif text == u'4 kap. kulturminneslagen.  Kyrkligt kulturminne' or text == u'Kyrkligt kulturminne. 4 kap. KML':
            bbrDict['kyrka'] = True
            return u'Kyrkligt kulturminne'
        elif text == u'Förordning (1988:1229) om statligt byggnadsminne m.m.' or text == u'Statligt byggnadsminne (SBM). Förordning (2013:558)':
            return u'Statligt byggnadsminne'
        elif text.startswith(u'Hävt '):
            return 'cancled'
        else:
            bbrDict['problem'].append((u'Okänt skydd', text))
            return None
    #
    @staticmethod
    def commonsPics(bbrDict, idList):
        u'''kollar om det finns uppmärkta bilder på Commons'''
        num=0
        for idnr in idList: #since both bbra and multiple bbrb
            filename = u'https://commons.wikimedia.org/w/api.php?action=query&list=exturlusage&format=xml&euprop=title&euquery=kulturarvsdata.se/raa/%s/html/%s&eunamespace=6&euoffset=0&eulimit=5' % (idnr[1], idnr[0])
            try:
                fil = urllib2.urlopen(filename)
            except HTTPError, e:
                bbrDict['problem'].append((u'commons-problem: httpError för %s' % filename, u'Felkod: %d' % e.code))
                return None
            except URLError, e:
                bbrDict['problem'].append((u'commons-problem: urlError för %s' % filename, cgi.escape(e.reason[0])))
                return None
            else:
                dom = parse(fil)
                fil.close()
                del fil
                items = dom.getElementsByTagName('eu')
                #antal träffar
                num += len(items)
                if not num == 0:                   #finns det några alls? 
                    bbrDict['bildCommons'] = items[0].attributes['title'].value[5:]
                    break
        del dom
        return num
    #
    @staticmethod
    def createTemplate(bbrDict):
        txt =u'{{Infobox byggnad|Byggnad\n'
        txt +=u' | namn         = %s\n' % bbrDict['namn']
        txt +=u' | kategori     = '
        if 'kategorier' in bbrDict.keys() and len(bbrDict['kategorier'])>0:
            for k in bbrDict['kategorier']:
                txt += '%s, ' % k
            txt = txt[:-2]
        txt +='\n'
        txt +=u' | bild         = '
        if 'bildCommons' in bbrDict.keys():
            txt += bbrDict['bildCommons']
        txt +='\n'
        txt +=u' | bild_text    = \n'
        txt +=u' | land         = [[Sverige]]\n'
        txt +=u' | distrikt     = [[{{safesubst:Användare:Lokal Profil/nycklar/län|%s}}|%s]]  | distrikt_etikett = Län\n' %(bbrDict['lan'],bbrDict['lanName'])
        txt +=u' | kommun       = [[{{safesubst:Användare:Lokal Profil/nycklar/kommuner|%s}}|%s]]\n' %(bbrDict['kommun'],bbrDict['kommunName'])
        txt +=u' | ort          = \n'
        txt +=u' | adress       = \n'
        txt +=u' | coord        = '
        if ('latitude' in bbrDict.keys()) and (len(bbrDict['latitude'])>0):
            txt += u'{{coord|%s|%s|display=inline,title|type:landmark}}' % (bbrDict['latitude'], bbrDict['longitude'])
        txt +=u'\n'
        txt +=u' <!-- Kulturskydd -->\n'
        if len(bbrDict['skydd'])>0:
            txt +=u' | skydd        = %s\n' % bbrDict['skydd'][0][2]
            txt +=u' | skydd_start  = %s\n' % bbrDict['skydd'][0][0]
            txt +=u' | skydd_slut   = %s\n' % bbrDict['skydd'][0][1]
            txt +=u' | skydd_nr     = {{BBR-länk|%s|%s|text=%s}}\n' % (bbrDict['id'], bbrDict['typ'][3:], bbrDict['reg-nr'])
            if len(bbrDict['skydd'])>1:
                i = 1
                while i < len(bbrDict['skydd']):
                    txt +=u' | skydd%d       = %s\n' % ((i+1),bbrDict['skydd'][i][2])
                    txt +=u' | skydd%d_start = %s\n' % ((i+1),bbrDict['skydd'][i][0])
                    txt +=u' | skydd%d_slut  = %s\n' % ((i+1),bbrDict['skydd'][i][1])
                    txt +=u' | skydd%d_nr    = {{BBR-länk|%s|%s|text=%s}}\n' % ((i+1),bbrDict['id'], bbrDict['typ'][3:], bbrDict['reg-nr'])
                    i +=1
        else:
            txt +=u' | skydd        = \n'
            txt +=u' | skydd_start  = \n'
            txt +=u' | skydd_slut   = \n' 
            txt +=u' | skydd_nr     = \n'
        if bbrDict['kyrka']:
            txt +=u' <!-- Religiösa byggnader -->\n'
            txt +=u' | trossamfund  = [[Svenska kyrkan]]\n'
            if 'stift' in bbrDict.keys() and bbrDict['stift']>0:
                txt +=u' | stift        = [[%s]]\n' % bbrDict['stift']
                txt +=u' | församling   = [[%s]]\n' % bbrDict['forsamling']
            else:
                txt +=u' | stift        = \n'
                txt +=u' | församling   = \n'
        txt +=u' <!-- Annat -->\n'
        txt +=u' | arkitekt     = '
        if 'arkitekt' in bbrDict.keys() and bbrDict['arkitekt']>0:
            txt += u'[[%s]]' % bbrDict['arkitekt']
        txt +=u'\n'
        if 'arkitekt_etikett' in bbrDict.keys():
            txt += u' | arkitekt_etikett = %s\n' % bbrDict['arkitekt_etikett']
        txt +=u' | konstruktör  = \n'
        txt +=u' | byggherre    = '
        if 'byggherre' in bbrDict.keys() and bbrDict['byggherre']>0:
            txt += u'[[%s]]' % bbrDict['byggherre']
        txt +=u'\n'
        txt +=u' | ägare        = \n'
        if 'byggstart' in bbrDict.keys():
            txt +=u' | byggstart    = %s\n' % bbrDict['byggstart']
        txt +=u' | färdig       = '
        if 'fardig' in bbrDict.keys() and bbrDict['fardig']>0:
            txt += u'%s' % bbrDict['fardig']
        txt +=u'\n'
        if ('andring' in bbrDict.keys()) and (len(bbrDict['andring'])>0):
            txt +=u' | ändrad       = %s\n' % bbrDict['andring'][0][1]
            txt +=u' | ändrad_år    = %s\n' % bbrDict['andring'][0][0]
            if len(bbrDict['andring'])>1:
                i = 1
                while i < len(bbrDict['andring']):
                    txt +=u' | ändrad%d      = %s\n' % (i,bbrDict['andring'][i][1])
                    txt +=u' | ändrad%d_år   = %s\n' % (i,bbrDict['andring'][i][0])
                    i += 1
        txt +=u' | stil         = \n'
        txt +=u' | konstruktion = \n'
        txt +=u' | material     = \n'
        if len(bbrDict['skydd'])==0:
            txt +=u' | bbr         = {{BBR-länk|%s|%s|text=%s}}\n' % (bbrDict['id'], bbrDict['typ'][3:], bbrDict['reg-nr'])
        txt +=u' | fotnoter     = \n'
        txt +=u'}}'
        return txt
#
class Format:
    @staticmethod
    def dateInterpreter(fromTime, toTime, swe=True):
        '''Given a fromTime and a toTime of the form YYYY-MM-DD this returns an interpretation stripped of dummy variables'''
        if (fromTime[5:] == '01-01') and (toTime[5:] == '12-31'): # end and start of year are nomally just dummy markup for info
            fromTime = fromTime[:4]
            toTime   = toTime[:4]
            if fromTime==toTime:
                return (fromTime,)
            elif (fromTime[:3]==toTime[:3]) and (fromTime[-1:] == '0') and (toTime[-1:] == '9'):  # dummy markup for decade
                return ('%s-talet' % fromTime,)
            elif (fromTime[:2]==toTime[:2]) and (fromTime[-2:] == '00') and (toTime[-2:] == '99'):  # dummy markup for century
                return ('%s-talet' % fromTime,)
            else:
                return (fromTime,toTime)
        elif fromTime==toTime:
            if swe:
                return (sweDate(fromTime),)
            else:
                return (fromTime,)
        else:
            if swe:
                return (sweDate(fromTime),sweDate(toTime))
            else:
                return (fromTime,toTime)
    @staticmethod
    def sweDate(date):
        '''ISO date (YYYY-MM-DD) to swedish date (DD Month YYYY)'''
        if (not len(date)==10) or (not date[7]=='-'): # second check needed since YYYY-talet is same length
            return date
        else:
            month = ('januari','februari','mars','april','maj','juni','juli','augusti','september','oktober','november','december')
            return '%d %s %s' %(int(date[-2:]), month[int(date[5:7])-1], date[:4])
    @staticmethod
    def urlencode(aDict):
        '''This ensures that every object of a dict is utf-8 encoded before geting urlencoded'''
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

app = webapp2.WSGIApplication([('/bbr/', MainPage),
                               ('/bbr/filter', Filter),
                               ('/bbr/bbra', BBRA),
                               ('/bbr/bbrb', BBRB)],
                              debug=True)
