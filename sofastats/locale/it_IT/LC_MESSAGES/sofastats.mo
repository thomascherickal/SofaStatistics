��    l      |  �   �      0	  Z   1	  �   �	  �   w
  #        %     2  =   I  ?   �     �     �  �   �  g   �  [   �     R     p  8   �  6   �     �  (        8     U  -   r  <   �     �  
   �  6         ?  "   `  +   �     �     �  L  �     /  	   8  &   B  i  i  %   �  )   �  7   #  H   [  �   �  �   O     �     �  	   �     �     �  "        9  )   E     o  y   �     �  #     X   <  ;   �  Q   �  C   #  |   g  m   �  D   R     �     �     �  Q   �  \    .   b  +   �     �     �     �     �  
   �     �     �       	             "     )     2  	   C  
   M     X  6   d  (   �     �     �  h   �  T   ;  L   �  :   �          6     =     @     X  a   r     �     �     �     �     �     �                 +   �  1   e   �!  �   1"  �   %#  &   �#     �#     �#  G   $  J   O$     �$     �$  �   �$  q   z%  _   �%     L&  "   h&  >   �&  >   �&     	'  )   &'  !   P'  !   r'  -   �'  Y   �'  #   (  
   @(  I   K(  )   �(  $   �(  -   �(     )  !   *)  �  L)     �,     �,  )   �,  w  (-  +   �.  ,   �.  5   �.  _   //  �   �/  }   `0     �0     �0     �0     �0     1  $   41     Y1  2   e1     �1  �   �1  !   J2  %   l2  G   �2     �2  G   �2  &   B3  c   i3  E   �3  %   4     94     H4     P4  D   _4  G  �4  7   �5  +   $6     P6     V6     f6     x6  
   �6  
   �6      �6     �6  	   �6     �6     �6  	   �6     �6  	   7     7     7  I   ,7  1   v7     �7     �7  w   �7  X   .8  W   �8  B   �8     "9     >9     F9     J9  "   i9  e   �9     �9     �9  	   :     :     :     :      &:     G:     d:     g                        b               J   -       *   Q   "   L   .         ,               W       \   !      F   M             +          a       c   f   6             0   U   T   G           _             h   R   A   =      ^   `   %       #       )   3   O   Y       l           ]       P   <      E   H          	       B         Z                      &       N   C   d   /   [       
   V   5   S   4   X       7   2   i      k       @   K          I          $           e   j       >      8   D   (       ?         :   '   ;      9                 1    

At least one field contained a single dot '.'.  This was converted into a missing value. 

Database "%s" didn't have any tables. You can only connect to SQLite databases which have data in them.

If you just wanted an empty SQLite database to put fresh data into from within SOFA, use the supplied sofa_db database instead. 

You can check your imported data by clicking the 'Enter/Edit Data' button on the main form. You'll find your data in the '%s' database. 
or the missing value character (.)  (Read Only)  (and optionally rows)  A default database is required unless the user is 'postgres'  is not a valid datetime.

Either enter a valid date/ datetime
  to the default SOFA database  vs  "%(new_fldname)s" already has value labels set. Only add labels here if you wish to add to or override existing value labels

Existing labels:

%(existing_labels)s "%(varlbl)s" has a variable selected but the previous drop down list "%(lbl_with_no_select)s" does not. "%s" is not a valid number.

Either enter a valid number or the missing value character (.) %(laba)s and %(labb)s - %(y)s %(lower)s to < %(upper)s %(max)s can only be on the right side e.g. %(max)s TO 12 %(min)s can only be on the left side e.g.%(min)s TO 12 %s (Read only column) %s has already been used as a field name %s is a reserved field name. %s is not a valid field type %s will not allow missing values to be stored (don't quote strings e.g. John not "John". Null for missing) (enter a filter e.g. agegp > 5) (filtered) (scroll down for details of all your database engines) * add, delete or rename fields,  * change the data type of fields,  * recode values from one field into another * rename data tables,  ... or add a new data table 1. If you are trying to recode a range e.g. ages 1-19 into a single age group,
put 1 TO 19 in the FROM original value(s) column, not 1 in the first column and 19 in the second.

2. Ranges use the keyword TO e.g. "150 TO 250". All keywords must be upper case, so "TO" will work but "to" will not.

3. "MIN" and "MAX" can be used in ranges e.g. "MIN TO 100", or "100 TO MAX". You can even use "MIN TO MAX" if you
want to leave out missing values.

4. "REMAINING" and "MISSING" are the two remaining keywords you can use
e.g. if you want all missing values to become 99 you would have a line with From as "MISSING", and To as 99

5. Only one condition is allowed per line. So if you want to recode <=5 and 10+ to 99 you would have one line with

    "MIN TO 5" as From and 99 as To

    and another line with

    "10 TO MAX" as From and 99 as To. 2 groups 3 or more <p class='gui-msg-medium'>Example data <p>There are not enough suitable variables available for this analysis. Only variables with a %s data type can be used in this analysis.</p><p>This problem sometimes occurs when numeric data is accidentally imported from a spreadsheet as text. In such cases the solution is to format the data columns to a numeric format in the spreadsheet and re-import it.</p> <p>Waiting for a chart to be run.</p> <p>Waiting for an analysis to be run.</p> <p>Waiting for at least one field to be configured.</p> A file name must be supplied when importing if running in headless mode. A mix of data types was found in a sample of data in "%(fldname)s".

First inconsistency:%(details)s

Please select the data type you want this entire column imported as. A table named "%(tbl)s" already exists in the SOFA default database.

Do you want to replace it with the new data from "%(fil)s"? ANOVA Add Add Under Add and configure columns Add and configure rows Add and configure rows and columns Algorithm:  All data in table included - no filtering Also add%sto report Although the distribution of %s is not perfectly 'normal', it may still be 'normal' enough for use. View graph to decide. Analysis of variance table Answering questions about your data Answers the question, are the elements of paired sets of data different from each other? Answers the question, do 2 groups have a different average? Answers the question, do 2 groups have different results (higher or lower ranks)? Answers the question, do 3 or more groups have a different average? Answers the question, do two variables change together. E.g. if one increases, the other also increases (or stays the same). Answers the question, is there a linear relationship between two variables i.e. do they both change together? Answers the question, is there a relationship between two variables. Any file Apply Apply filter Are "%(a)s" and "%(b)s" correlated - do they change together in a linear fashion? Are you looking at the difference between two groups or more?

Example with 2 groups: average vocabulary of Males vs Females.

Example with 3 or more groups: average sales figures for the North, South, East, and West regions

You can look at how many groups your data has by clicking on the "%s" button down the bottom and running a Frequency Table Assess data type e.g. categorical, ordered etc Assess the normality of your numerical data Averaged Avg Rank Brief Explanation Browse Browse ... By Value CI 95% CONFIGURE TEST CSV FILE? Value Values Variable Variable Details Variables Version %s View Report View selected HTML output file in your default browser Waiting for a spreadsheet to be selected X-axis Y-axis You can only use letters, numbers and underscores in a SOFA Table Name. Use another name?
Orig error: %s You can only use letters, numbers and underscores in a SOFA name.  Use another name? You will need to save the changes you made first. Save changes and continue? Your new table has been added to the default SOFA database cells with expected count < 5 column df e.g. age into age group is invalid for data type  is longer than the maximum of %s. Either enter a shorter value or the missing value character (.) nominal p value quantity row suitable t statistic t-test - independent t-test - paired table Project-Id-Version: sofastatistics
Report-Msgid-Bugs-To: FULL NAME <EMAIL@ADDRESS>
POT-Creation-Date: 2013-12-18 07:10+1300
PO-Revision-Date: 2015-04-13 11:33+0000
Last-Translator: Domenico <Unknown>
Language-Team: Italian <it@li.org>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit
X-Launchpad-Export-Date: 2016-04-05 07:32+0000
X-Generator: Launchpad (build 17972)
 

Almeno un campo conteneva un punto singolo  '.'.  Questo è stato convertito in un valore mancante. 

Il database "%s" non conteneva alcuna tabella. Puoi connetterti solo ai database SQLite che contengono dei dati.

Se vuoi semplicemente un database SQLite vuoto per inserire nuovi dati utilizzando SOFA puoi usare il database sofa_db fornito. 

Puoi controllare l'importazione dei tuoi dati facendo clic sul bottone  'Enter/Edit Data' nel form principale. Troverai i tuoi dati nel database  '%s' 
o il carattere di valore mancante (.)  (Solo Lettura)  (od anche righe)  Un database di default è richiesto a meno che l'utente sia 'postgres'  non è un data o un orario valido

Inserisci una data o un orario valido
  al database SOFA di default.  vs  "%(new_fldname)s" ha già delle etichette dei valori impostate. Aggiungi delle etichette quisolo se vuoi aggiungere o sostituire quelle esistenti

Etichette esistenti:

%(existing_labels)s "%(varlbl)s" ha una variabile selezionata, ma l'elenco a discesa precedente "%(lbl_with_no_select)s" ne è privo. "%s" non è un numero valido.

Inserisci un numero valido o il carattere di valore mancante (.) %(laba)s e %(labb)s - %(y)s da %(lower)s a %(upper)s (escluso) %(max)s può essere usato solo a destra, ad es. 12 TO  %(max)s %(min)s può essere usato solo a sinistra ad es. %(min)s TO 12 %s (colonna di sola lettura) %s è già stato usato come nome di campo %s è un nome di campo riservato. %s non è un tipo di campo valido %s non permetterà di salvare valori mancanti (non scrivere le stringhe tra virgolette es. John e non "John". Null per valore mancante) (inserisci un filtro es. agegp > 5) (filtrato) (scorri verso il basso per i dettagli su tutti i tuoi motori di database) * aggiunge, cancella o rinomina i campi,  * cambia il tipo di dati del campo,  * ricodifica i valori da un campo ad un altro * rinomina le tabelle,  d... o aggiungi una nuova tabella 1. Se stai cercando di ricodificare un intervallo ad es. età 1-19 in un singolo gruppo di età,
inserisci 1 TO 19 nella colonna FROM original value(s), non 1 nella prima colonna e 19 nella seconda.

2. Gli intervalli usano la parola chiave TO es. "150 TO 250". Tutte le parole chiave devono essere maiuscole, quindi "TO" funzionerà mentre "to" no.

3. "MIN" e "MAX" possono essere usati negli intervalli, es. "MIN TO 100", oppure "100 TO MAX". Puoi usare anche "MIN TO MAX" 
se vuoi lasciar fuori i valori mancanti.

4. "REMAINING" e "MISSING" sono le rimanenti parole chiave che puoi usare
as. se vuoi che tutti i valori mancanti diventino 99 avrai una riga con "MISSING" come From e 99 come To

5. E' ammessa solo una condizione per riga. Quindi se vuoi ricodificare i valori <=5 e 10+ come 99 avrai una riga con

    "MIN TO 5" come From e 99 come To

    ed un'altra riga con

    "10 TO MAX" come From e 99 come To. 2 gruppi 3 o superiore <p class='gui-msg-medium'>Dati di esempio <p>Non ci sono abbastanza variabili per questa analisi. Solo le variabili di tipo %s possono essere usate in questa analisi</p><p>A volte questo problema si presenta quando dei dati numerici vengono importati da un foglio di calcolo come testo. In questi casi la soluzione è formattare le colonne di dati con un formato numerico nel foglio di calcolo e poi reimportarlo.</p> <p>In attesa di un grafico da generare.</p> <p>In attesa di una analisi da eseguire.</p> <p>In attesa che almeno un campo sia configurato.</p> Quando si esegue l'importazione in modalità headless è obbligatorio indicare un nome di file. Sono stati trovati tipi di dati diversi in un campione di dati del campo "%(fldname)s".

Prima inconsistenza:%(details)s

Seleziona il tipo di dati che vuoi assegnare a tutti dati importati da questa colonna. Esiste già una tabella chiamata "%(tbl)s" nel database di default di  SOFA.

Vuoi sostituirla con i nuovi dati da "%(fil)s"? ANOVA Aggiungi Aggiungi sotto Aggiungi e configura colonne Aggiungi e configura righe Aggiungi e configura righe e colonne Algoritmo:  Inclusi tutti i dati della tabella - nessun filtro Aggiungi anche  %sto report Anche se la distribuzione di %s non è perfettamente 'normale' potrebbe essere 'normale' abbastanza per essere usata. Guarda il grafico per decidere. Analisi della tabella di varianza Rispondere alle domande sui tuoi dati Gli elementi di insiemi di dati appaiati sono diversi l'uno dall'altro? Due gruppi hanno medie diverse? Due gruppi hanno risultati diversi (intervalli più alti o più bassi)? Tre o più gruppi hanno medie diverse? Due variabili cambiano insieme, ad es. se una cresce cresce anche l'altra (o invece rimane uguale)? C'è una relazione lineare tra due variabili, cioè cambiano insieme? C'è una relazione tra due variabili? Qualsiasi file Applica Applica filtro "%(a)s" e "%(b)s" sono correlate - cambiano insieme in modo lineare? Stai cercando le differenze tra due o più gruppi?

Esempio con 2 gruppi: vocabolario medio di Maschi e Femmine.

Esempio con 3 o più gruppi: media delle vendite per regioni del Nord, Centro, Sud e Isole

Puoi vedere quanti gruppi hanno i tuoi dati cliccando sul pulsante "%s" in fondo ed eseguendo una Tabella delle frequenze Valuta il tipo di dati, ad es. categorie, ordinali ecc. Valuta la normalità dei tuoi dati numerici Media Posizione media Breve spiegazione Sfoglia Sfoglia... Per valore Intervallo di Confidenza del 95% Configura il test File CSV? Valore Valori Variabile Dettagli della Variabile Variabili Versione %s Visualizza Report Visualizza il file di output  HTML selezionato nel tuo browser di default In attesa della selezione di un foglio di calcolo Asse X Asse Y Puoi usare solo lettere, numeri e  underscore nel nome della Tabella in  SOFA. Utilizzare un altro nome?
Orig error: %s Puoi usare solo lettere, numeri e underscore nei nomi di SOFA. Vuoi usare un altro nome? Sarà necessario salvare prima i cambiamenti fatti. Salvare i cambiamenti e continuare? La tua nuova tabella è stata aggiunta al database SOFA di default celle con valore atteso < 5 colonna gdl per es. l'età nel gruppo età non è valido per il tipo di dato  è più lungo del massimo di %s. Inserisci un valore più corto o il carattere di valore mancante (.) nominale p value quantità riga adatto statistica t t-test per campioni indipendenti t-test per campioni appaiati tabella 