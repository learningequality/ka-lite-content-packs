contentpack: pex
	mkdir -p out/
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite en 0.17 --out=out/en.zip
	./makecontentpacks minimize-content-pack.py out/en.zip out/en-minimal.zip
	./makecontentpacks extract_khan_assessment.py out/en.zip
	./makecontentpacks collectmetadata.py out/ --out=out/all_metadata.json

ar: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite ar 0.17 --out=out/langpacks/ar.zip --no-assessment-resource

bg: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bg 0.17 --out=out/langpacks/bg.zip --no-assessment-resources

bn: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite bn 0.17 --out=out/langpacks/bn.zip --no-assessment-resources

da: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite da 0.17 --out=out/langpacks/da.zip --no-assessment-resources

de: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite de 0.17 --out=out/langpacks/de.zip --no-assessment-resources

es: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite es 0.17 --out=out/langpacks/es.zip --no-assessment-resources --subtitlelang=es --interfacelang=es-ES --contentlang=es-ES

fr: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite fr 0.17 --out=out/langpacks/fr.zip

id: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite id 0.17 --out=out/langpacks/id.zip --no-assessment-resource

hi: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite hi 0.17 --out=out/langpacks/hi.zip --no-assessment-resource

ka: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite ka 0.17 --out=out/langpacks/ka.zip --no-assessment-resources

pl: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pl 0.17 --out=out/langpacks/pl.zip --no-assessment-resources

pt-BR: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-BR 0.17 --out=out/langpacks/pt-BR.zip --no-assessment-resources --videolang=pt-BR --contentlang=pt-BR

pt-PT: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite pt-PT 0.17 --out=out/langpacks/pt-PT.zip --no-assessment-resources --videolang=pt-PT --contentlang=pt-PT

xh: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite xh 0.17 --out=out/langpacks/xh.zip --no-assessment-resource

sw: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite sw 0.17 --out=out/langpacks/sw.zip --no-assessment-resources --videolang=sw --subtitlelang=sw


ta: pex
	PEX_MODULE=contentpacks ./makecontentpacks ka-lite ta 0.17 --out=out/langpacks/ta.zip --no-assessment-resource


all: supported


langpacks: pt-PT es pt-BR bn de fr da bg id hi xh ta ka sw
	unzip -p out/en.zip content.db > content.db
	./makecontentpacks collectmetadata.py out/langpacks/ --out=out/all_metadata.json


sdist:
	python setup.py sdist


pex: sdist
	pex --python=python3 -r requirements.txt -o makecontentpacks --disable-cache --no-wheel dist/content-pack-maker-`python setup.py --version`.tar.gz


publish:
	scp -P 4242 out/*.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/
	scp -P 4242 out/khan_assessment.zip $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/
	scp -P 4242 all_metadata.json $(sshuser)@pantry.learningequality.org:/var/www/downloads/$(project)/$(version)/content/contentpacks/


dubbed-video-csv: pex
	./makecontentpacks ./contentpacks/update_dubbed_video_spreadsheet.py
