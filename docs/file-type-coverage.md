# ForgeVault File Type Coverage

ForgeVault should behave like a real manufacturing vault, not a narrow drawing viewer.

It must index and preserve every file type commonly used in engineering, quality, manufacturing, CAM, additive manufacturing, ERP handoffs, customer portals, and supplier documentation.

## Rule

Unknown file types must still be indexable.

ForgeVault should classify what it knows and safely preserve what it does not know.

Do not reject files just because preview support is not implemented yet.

## Current implementation

The code registry lives at:

```text
backend/forgevault/file_types.py
```

Folder indexing attaches file type metadata under:

```text
version_metadata.file_type
```

Example metadata:

```json
{
  "extension": ".sldprt",
  "category": "solidworks",
  "label": "SOLIDWORKS Part",
  "preview_strategy": "cad3d",
  "vault_relevant": true,
  "known_type": true
}
```

Unknown example:

```json
{
  "extension": ".weirdcustomerfile",
  "category": "unknown",
  "label": "Unknown File Type",
  "preview_strategy": "metadata",
  "vault_relevant": true,
  "known_type": false
}
```

## Covered categories

### SOLIDWORKS

```text
.sldprt
.sldasm
.slddrw
.prtdot
.asmdot
.drwdot
```

### Autodesk Inventor

```text
.ipt
.iam
.idw
.ipn
```

### AutoCAD and Autodesk

```text
.dwg
.dwt
.dws
.dxf
.f3d
.f3z
.dwf
.dwfx
```

### Neutral CAD

```text
.step
.stp
.iges
.igs
.x_t
.x_b
.xmt_txt
.xmt_bin
.sat
.sab
.jt
.prc
.3dxml
```

### CATIA

```text
.catpart
.catproduct
.catdrawing
.cgr
.model
.exp
.session
```

### Creo / ProE

```text
.prt
.asm
.drw
.neu
.xpr
.xas
```

### Siemens NX

```text
.prt
.fem
.sim
```

### Solid Edge

```text
.par
.asm
.dft
.psm
```

### 3D mesh / visualization

```text
.stl
.obj
.mtl
.3mf
.amf
.ply
.wrl
.vrml
.x3d
.dae
.gltf
.glb
.usd
.usda
.usdc
.usdz
.fbx
```

### CAM / CNC

```text
.gcode
.gco
.nc
.cnc
.tap
.eia
.min
.cam
.mcam
.mcamx
.sprut
.ncc
.hsm
.fmp
.tools
.tool
.hsmlib
.library
.nst
.nest
.lcc
.ord
.dnc
```

### Additive manufacturing

```text
.3mf
.amf
.gcode
.bgcode
.factory
.form
.lys
.ctb
.photon
.pwmo
.sl1
.sl1s
.ini
.json
.yaml
.yml
.cfg
.conf
```

### Drawing and document files

```text
.pdf
.tif
.tiff
.jpg
.jpeg
.png
.bmp
.gif
.webp
.heic
.svg
.plt
.hpgl
.cal
.cals
```

### Office / business docs

```text
.xls
.xlsx
.xlsm
.xlsb
.xltx
.xltm
.csv
.doc
.docx
.docm
.dotx
.dotm
.rtf
.odt
.ppt
.pptx
.pptm
.ppsx
.odp
.txt
.md
.log
.xml
.html
.htm
```

### Quality / ERP / labels

```text
.fai
.fair
.ppap
.cmm
.iqc
.oqc
.btw
.lbl
.zpl
.epl
.prn
```

### Archives and email

```text
.zip
.7z
.rar
.tar
.gz
.tgz
.bz2
.xz
.cab
.eml
.msg
.oft
```

### Software/config

```text
.py
.ps1
.bat
.cmd
.sh
.js
.ts
.cs
.cpp
.c
.h
.hpp
.java
.kt
.rs
.go
.json
.yaml
.yml
.toml
.ini
.cfg
.conf
.env
.properties
```

## Preview strategies

Current planned preview strategy labels:

```text
metadata
text
image
pdf
drawing
cad3d
mesh3d
spreadsheet
document
archive
```

Preview support does not need to exist for indexing to work.

Index first. Preview later.

## Important limitation

Some extensions are ambiguous.

Examples:

```text
.prt can mean Creo/ProE or Siemens NX
.asm can mean Creo/ProE or Solid Edge
.drw can mean Creo/ProE drawing or other drawing file
```

ForgeVault should resolve ambiguous types later using metadata plugins, folder rules, customer rules, or file sniffing.

## Future enhancement path

1. Detect by extension.
2. Add MIME/file sniffing.
3. Add lightweight preview for image/PDF/text/spreadsheet.
4. Add DXF parsing.
5. Add 3MF/STL/OBJ/glTF mesh preview.
6. Add CAD metadata extraction where practical.
7. Add plugin hooks for SOLIDWORKS/Inventor if installed locally.
8. Add customer-specific naming and identity plugins.

## Product rule

ForgeVault should never become useless because it cannot preview a file.

A vault must preserve, identify, search, version, check out, check in, and review files first.

Preview is a convenience layer, not the definition of support.
